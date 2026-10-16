"""Download a shared Google Photos album: metadata, previews and numbered contact sheets.

Usage (run inside a new album folder):
    python3 fetch_album.py "https://photos.app.goo.gl/XXXX"   # or the full photos.google.com/share/...?key=... URL

Writes items.json (one row per photo, numbered 1..N by camera time), thumbs/NNN.jpg (600 px),
sheets/sheet_AAA-BBB.jpg (20 numbered photos per sheet, for reviewing) and photo stats
(sharpness, brightness, contrast, saturation) used later for tuning.
The public share link works without signing in, but it hides GPS locations (see SKILL.md).
"""
import json
import os
import re
import subprocess
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone

import numpy as np
from PIL import Image, ImageDraw, ImageFont

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128 Safari/537.36"


def curl(url: str, data: str | None = None) -> str:
    """GET/POST with curl (python's own SSL certs fail on this Mac)."""
    cmd = ["curl", "-sL", "-A", UA, url]
    if data is not None:
        cmd[2:2] = ["-H", "Content-Type: application/x-www-form-urlencoded;charset=UTF-8", "--data", data]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=120).stdout


def resolve(url: str) -> str:
    """photos.app.goo.gl short links open an interstitial page; find the real share URL inside it."""
    if "photos.google.com/share" in url:
        return url
    # with a non-browser user agent the short link answers with a plain 302 redirect
    loc = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{redirect_url}", "-A", "curl/8", url],
                         capture_output=True, text=True, timeout=60).stdout.strip()
    m = re.match(r"https://photos\.google\.com/share/\S+", loc)
    if not m:
        sys.exit("Could not resolve the short link — open it in the browser and paste the full photos.google.com/share/... URL")
    return m.group(0).replace("\\u0026", "&").replace("&amp;", "&")


def items_from_share(url: str) -> list[list]:
    """All album items: first 300 are in the page (AF_initDataCallback ds:1), the rest via the snAcKc RPC."""
    html = curl(url + ("&" if "?" in url else "?") + "hl=en")
    m = re.search(r"AF_initDataCallback\(\{key: 'ds:1'.*?data:(.*?), sideChannel: \{\}\}\);", html, re.S)
    d = json.loads(m.group(1))
    items, tok, album, key = list(d[1]), d[2], d[3][0], d[3][19]
    fsid = re.search(r'"FdrFJe":"([^"]+)"', html).group(1)
    bl = re.search(r'"cfb2h":"([^"]+)"', html).group(1)
    while tok:
        req = [[["snAcKc", json.dumps([album, tok, None, key]), None, "generic"]]]
        body = urllib.parse.urlencode({"f.req": json.dumps(req)})
        rpc = (f"https://photos.google.com/_/PhotosUi/data/batchexecute?rpcids=snAcKc&source-path=/share/{album}"
               f"&f.sid={fsid}&bl={bl}&hl=en&_reqid=123456&rt=c")
        line = next(l for l in curl(rpc, body).split("\n") if "wrb.fr" in l)
        p = json.loads(json.loads(line)[0][2])
        items += p[1] or []
        tok = p[2]
    print(f"album {album[:12]}…: {len(items)} items")
    return items


def stats(im: Image.Image) -> dict[str, float]:
    """Sharpness (Laplacian variance), brightness, contrast, saturation of a preview."""
    g = np.asarray(im.convert("L"), dtype=float)
    lap = g[1:-1, 1:-1] * 4 - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    hsv = np.asarray(im.convert("HSV"), dtype=float)
    return {"sharp": round(float(lap.var()), 1), "bright": round(float(g.mean()), 1),
            "contrast": round(float(g.std()), 1), "sat": round(float(hsv[..., 1].mean()), 1)}


def main() -> None:
    """Fetch everything into the current folder."""
    url = resolve(sys.argv[1])
    items = sorted(items_from_share(url), key=lambda x: x[2])  # camera time order
    os.makedirs("thumbs", exist_ok=True)
    os.makedirs("sheets", exist_ok=True)
    rows = [{"n": i + 1, "id": x[0], "url": x[1][0], "w": x[1][1], "h": x[1][2], "ts": x[2], "tz": x[4] or 0}
            for i, x in enumerate(items)]
    jobs = "\n".join(f"{r['url']}=w600-h600 thumbs/{r['n']:03d}.jpg" for r in rows)
    subprocess.run(["bash", "-c", "xargs -P 12 -L 1 bash -c 'curl -s -o \"$1\" \"$0\"'"], input=jobs, text=True)
    prev = None
    for r in rows:
        im = Image.open(f"thumbs/{r['n']:03d}.jpg").convert("RGB")
        r.update(stats(im))
        r["mp"] = round(r["w"] * r["h"] / 1e6, 1)
        r["orient"] = "L" if r["w"] > r["h"] * 1.05 else ("P" if r["h"] > r["w"] * 1.05 else "S")
        r["local"] = (datetime.fromtimestamp(r["ts"] / 1000, timezone.utc) + timedelta(milliseconds=r["tz"])).strftime("%Y-%m-%d %H:%M")
        r["gap_min"] = None if prev is None else round((r["ts"] - prev) / 60000)
        prev = r["ts"]
    json.dump(rows, open("items.json", "w"))
    # contact sheets: 5 x 4, number in a yellow box
    C, R, CW, CH = 5, 4, 400, 300
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 30)
    for s in range(0, len(rows), C * R):
        sheet = Image.new("RGB", (C * CW, R * CH), (30, 30, 30))
        d = ImageDraw.Draw(sheet)
        for k, r in enumerate(rows[s:s + C * R]):
            im = Image.open(f"thumbs/{r['n']:03d}.jpg").convert("RGB")
            im.thumbnail((CW - 6, CH - 6))
            cx, cy = (k % C) * CW, (k // C) * CH
            sheet.paste(im, (cx + (CW - im.width) // 2, cy + (CH - im.height) // 2))
            d.rectangle([cx, cy, cx + 64, cy + 38], fill=(255, 220, 0))
            d.text((cx + 5, cy + 3), str(r["n"]), fill=(0, 0, 0), font=font)
        sheet.save(f"sheets/sheet_{s + 1:03d}-{min(s + C * R, len(rows)):03d}.jpg", quality=85)
    days: dict[str, int] = {}
    for r in rows:
        days[r["local"][:10]] = days.get(r["local"][:10], 0) + 1
    print(f"{len(rows)} photos, {len(days)} days, {len(os.listdir('sheets'))} contact sheets")


if __name__ == "__main__":
    main()
