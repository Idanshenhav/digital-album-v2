"""Page titles for Lupa as images, in the plan's exact style.

Lupa's own page titles take their look from the theme (fixed font, a coloured box, no bold, no shadow,
45 characters). So each title is drawn here instead: the plan's font, bold, a colour that stands out with a soft
shadow, no box. The image's background is the exact page background under it (our blurred photo, or the theme's
flat colour), so it looks printed on the page. Run after lupa_layout.py; it adds the title frames to
ready/lupa_layout.json and writes ready/upload/title_*.jpg.

Rules it enforces (the script stops if one is broken):
- a title never touches a photo or a QR code
- a title never sits on a theme drawing: if the spread's theme background has a drawing there, the spread
  switches to the plain theme background of the closest colour ("bg" in the spread entry; lupa_apply.js sets it)
- titles stay inside Lupa's safe area (0.5 cm inside the trim)

Usage (album folder):  python3 lupa_titles.py
"""
import glob
import html
import json
import os
import re
import subprocess
import sys
import tempfile
import zlib
from datetime import datetime, timedelta

import numpy as np
from PIL import Image, ImageFilter

import album_config as C
import lupa_layout as LL
import make_upload_set as U

QR_PY = sys.executable  # the same Python (needs opencv for the scan check)
from chrome import CHROME, T
PLAN = C.OUTPUT_HTML
SW, SH, HALF, M, FOLD = LL.SW, LL.SH, LL.HALF, LL.M, LL.FOLD
MIN_PX = 820  # Lupa: photos under 800 x 800 px are refused
SAFE = 35 + 59  # bleed + 0.5 cm
TITLE_CY = 140  # title centre, px from the top trim (Lupa's top margin is 235 px; photos start below it)
BG_DIR = "ready/theme_bg"  # Lupa theme backgrounds (medium size, flat colours + small drawings)
# The book's Lupa theme, read from the live editor with claudeLupa.themeInfo() and saved as ready/lupa_theme.json
THEME = json.load(open("ready/lupa_theme.json")) if os.path.exists("ready/lupa_theme.json") else None
THEME_BG = THEME["url"] if THEME else getattr(C, "LUPA_THEME_BG_URL", "")
# theme background number of each spread as Lupa set it (the last spread may be a single page)
LIVE_BG = THEME["live"] if THEME else getattr(C, "LUPA_LIVE_BG", [])
BG_COUNT = THEME["count"] if THEME else 18
MEASURE_JS = r"""
<script>
window.addEventListener('load', () => setTimeout(() => {
  const out = [];
  document.querySelectorAll('.page[data-page]').forEach(p => {
    const R = p.getBoundingClientRect();
    const ts = [...p.querySelectorAll('.ptitle')].map(t => {
      const rg = document.createRange(); rg.selectNodeContents(t); const r = rg.getBoundingClientRect();
      return {text: t.innerText.trim(), x: (r.x - R.x) / R.width * 30, y: (r.y - R.y) / R.height * 22,
              w: r.width / R.width * 30, h: r.height / R.height * 22,
              fs: parseFloat(getComputedStyle(t).fontSize) / R.width * 30,
              ltr: !!t.querySelector('[dir=ltr]'), bottom: t.classList.contains('pbottom')};
    });
    if (ts.length) out.push({page: +p.dataset.page, titles: ts});
  });
  const pre = document.createElement('pre'); pre.id = 'measured'; pre.textContent = JSON.stringify(out);
  document.body.appendChild(pre);
}, 500));
</script>
"""


def measure() -> list[dict]:
    """Title text + position (cm on its page) for every titled page, read from the rendered plan."""
    src = open(PLAN, encoding="utf8").read()
    tmp = "_measure_titles.html"
    open(tmp, "w", encoding="utf8").write(src.replace("</body>", MEASURE_JS + "</body>"))
    try:
        dom = subprocess.run([*T(120), CHROME, "--headless=new", "--disable-gpu", "--window-size=1600,1000",
                              "--allow-file-access-from-files", "--virtual-time-budget=15000", "--dump-dom",
                              "file://" + os.path.abspath(tmp)], capture_output=True, text=True).stdout
    finally:
        os.remove(tmp)
    m = re.search(r'<pre id="measured">(.*?)</pre>', dom, re.S)
    if not m:
        raise SystemExit("could not measure the plan titles")
    return json.loads(html.unescape(m.group(1)))


def theme_bg(n: int, single: bool = False) -> Image.Image:
    """Theme background picture n (1..18), cached. single = one-page background (page 101)."""
    os.makedirs(BG_DIR, exist_ok=True)
    f = f"{BG_DIR}/{'page' if single else 'layflat'}_{n:02d}.jpg"
    if not os.path.exists(f):
        subprocess.run(["curl", "-s", "-o", f, THEME_BG.format("" if single else "layflat/", n)], check=True)
    return Image.open(f).convert("RGB")


def render_text(text: str, px: float, ink: str, ltr: bool, up: int = 1, strong: bool = False) -> Image.Image:
    """Title text in the plan's font (system UI, bold), transparent background, up x Lupa's pixel size
    (Lupa refuses photos under 800 x 800 px, so title images are stored large; printed size is unchanged)."""
    color, shadow = (("#ffffff", "0 1px 3px rgba(0,0,0,.55)") if ink == "light"
                     else ("#1f2328", "0 1px 2px rgba(255,255,255,.55)"))
    k = up
    if strong:  # busy texture behind: a soft halo all round the letters
        g = px * k / 61  # halo size follows the font size
        shadow = (f"0 0 {5 * g:.1f}px rgba(0,0,0,.85),0 0 {10 * g:.1f}px rgba(0,0,0,.6),0 {2 * g:.1f}px {3 * g:.1f}px rgba(0,0,0,.8)" if ink == "light"
                  else f"0 0 {5 * g:.1f}px rgba(255,255,255,.95),0 0 {10 * g:.1f}px rgba(255,255,255,.75)")
    page = (f"<html><body style='margin:0;background:transparent'><div dir='{'ltr' if ltr else 'rtl'}' "
            f"style='display:inline-block;padding:{px * k * .25:.0f}px;white-space:nowrap;"
            f"font-family:-apple-system,system-ui,\"Segoe UI\",Heebo,Arial,sans-serif;font-weight:700;"
            f"font-size:{px * k:.1f}px;color:{color};text-shadow:{shadow if strong else shadow.replace('1px', f'{k}px').replace('2px', f'{2 * k}px').replace('3px', f'{3 * k}px')}'>"
            f"{html.escape(text)}</div></body></html>")
    with tempfile.TemporaryDirectory() as d:
        open(f"{d}/t.html", "w", encoding="utf8").write(page)
        subprocess.run([*T(60), CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--default-background-color=00000000", f"--window-size={min(16300, int(len(text) * px * k * 0.62 + 400))},{int(px * k * 3)}",
                        f"--screenshot={d}/t.png", f"file://{d}/t.html"], capture_output=True, check=True)
        im = Image.open(f"{d}/t.png").convert("RGBA")
    box = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    im = im.crop(box)
    return im


def page_map(spread: dict, plan_pages: list[dict], page_no: int):
    """Plan cm on a page -> Lupa px on the spread (same scaling lupa_layout.place uses for that page's photos)."""
    pg = plan_pages[page_no - 1]
    right = page_no % 2 == 0
    if spread["type"] == "LAYFLAT_TYPE" and pg.get("merged"):
        bx, by, bw, bh = LL.SPREAD_BOX
        dx0, dy0, dx1, dy1 = M, M, SW - M, SH - M
        shift = 30.0 if right else 0.0
    else:
        bx, by, bw, bh = LL.BOX
        x0 = HALF - 1 if right else 0
        if spread["type"] != "LAYFLAT_TYPE":
            x0 = 0
        dx0, dy0, dx1, dy1 = (x0 + FOLD, M, x0 + HALF - M, SH - M) if right else (x0 + M, M, x0 + HALF - FOLD, SH - M)
        shift = 0.0
    s = min((dx1 - dx0) / bw, (dy1 - dy0) / bh)
    ox = dx0 + ((dx1 - dx0) - bw * s) / 2
    oy = dy0 + ((dy1 - dy0) - bh * s) / 2
    return (lambda x: ox + (x + shift - bx) * s), (lambda y: oy + (y - by) * s), s


def frame_box(f: dict) -> tuple:
    return f["x"] - f["w"] / 2, f["y"] - f["h"] / 2, f["x"] + f["w"] / 2, f["y"] + f["h"] / 2


def hits(a: tuple, b: tuple, gap: float = 12) -> bool:
    return a[0] < b[2] + gap and b[0] < a[2] + gap and a[1] < b[3] + gap and b[1] < a[3] + gap


def background(spread: dict, path_of: dict, box: tuple):
    """What lies under box on this spread: ('photo', image crop) for our full-spread blurred photo,
    ('theme', theme bg number) otherwise."""
    for f in spread["frames"]:
        fx0, fy0 = f["x"] - f["w"] / 2, f["y"] - f["h"] / 2  # a full-spread or full-page photo that covers the box
        if f.get("bleed") and f["w"] >= SW / 2 - 2 and f["k"] in path_of and fx0 - 2 <= box[0] and box[2] <= fx0 + f["w"] + 2:
            im = Image.open(path_of[f["k"]]).convert("RGB")
            fa, ia = f["w"] / f["h"], im.width / im.height  # lupa_apply.js trims the centre to the frame's shape
            cw, ch = (im.height * fa, im.height) if ia > fa else (im.width, im.width / fa)
            cx0, cy0 = (im.width - cw) / 2, (im.height - ch) / 2
            fx0, fy0 = f["x"] - f["w"] / 2, f["y"] - f["h"] / 2
            sx = cw / f["w"]
            return "photo", im.crop((round(cx0 + (box[0] - fx0) * sx), round(cy0 + (box[1] - fy0) * sx),
                                     round(cx0 + (box[2] - fx0) * sx), round(cy0 + (box[3] - fy0) * sx))).resize(
                (round(box[2] - box[0]), round(box[3] - box[1])), Image.LANCZOS)
    return "theme", None


def theme_patch(n: int, box: tuple, single: bool = False) -> np.ndarray:
    im = theme_bg(n, single)
    sx, sy = im.width / (HALF if single else SW), im.height / SH
    return np.asarray(im.crop((int(box[0] * sx), int(box[1] * sy), int(np.ceil(box[2] * sx)), int(np.ceil(box[3] * sy)))), float)


def on_photo(sp: dict, q: dict) -> float:
    """Share of a QR code's area that lies on a photo (QRs placed over a photo corner keep the photo's colour)."""
    a = frame_box(q)
    cover = 0.0
    for f in sp["frames"]:
        if f.get("bleed"):
            continue
        b = frame_box(f)
        cover += max(0, min(a[2], b[2]) - max(a[0], b[0])) * max(0, min(a[3], b[3]) - max(a[1], b[1]))
    return cover / ((a[2] - a[0]) * (a[3] - a[1]))


def is_plain(a: np.ndarray) -> bool:
    """No drawing in this part of the theme background (flat colour)."""
    return float(a.reshape(-1, 3).std(0).max()) < 6


def main() -> None:
    L = json.load(open("ready/lupa_layout.json"))
    plan_pages = json.load(open("plan.json"))["pages"]
    files = LL.upload_files()
    path_of = {LL.key_of(f): f for f in set(files.values())}
    path_of.update({LL.key_of(q["file"]): q["file"] for q in C.QR_CODES})
    path_of.update({LL.key_of(f): f for f in glob.glob("ready/upload/texbg_*.jpg")})
    for f in glob.glob("ready/upload/title_*.jpg"):
        os.remove(f)
    for s in L["spreads"]:
        s["frames"] = [f for f in s["frames"] if not f.get("title_tile")]
        s.pop("bg", None)
    measured = measure()
    # Each title's EXIF time comes from its own text (stable): one title dropping out or moving never shifts the
    # others, and a re-worded title gets a new time by itself, so Lupa never shows a stale copy.
    t0 = datetime(2001, 1, 1, 8, 0, 0)  # no photo is from this day
    count, report, taken = 0, [], set()
    # pass 1: where each title will sit; a theme background must be plain under every title of its spread
    probes: dict[int, list] = {}
    for m in measured:
        no = m["page"] - getattr(C, "OFF", 1)
        i = 0 if no == 1 else no // 2
        fx, fy, s = page_map(L["spreads"][i], plan_pages, no)
        for t in m["titles"]:
            x1, px = fx(t["x"] + t["w"]), t["fs"] * s
            cy = SH - TITLE_CY if t["bottom"] else TITLE_CY
            probe = (x1 - t["w"] * s - 60, cy - px, x1 + 60, cy + px)
            if background(L["spreads"][i], path_of, probe)[0] == "theme":
                probes.setdefault(i, []).append(probe)
    is_qr = lambda f: f.get("bleed") and f["n"] == 0 and f["w"] < HALF - 2 and not f.get("title_tile")
    for i, sp in enumerate(L["spreads"]):  # QR codes on a theme background: also no drawing under them
        for f in sp["frames"]:
            if is_qr(f) and background(sp, path_of, frame_box(f))[0] == "theme":
                probes.setdefault(i, []).append(frame_box(f))
    for i, ps in probes.items():
        single = L["spreads"][i]["type"] != "LAYFLAT_TYPE"
        full = (0, 0, HALF if single else SW, SH)
        clean = lambda n: all(is_plain(theme_patch(n, p, single)) for p in ps)
        if clean(LIVE_BG[i]):
            continue
        cur = theme_patch(LIVE_BG[i], full, single).reshape(-1, 3).mean(0)
        ok = [n for n in range(1, BG_COUNT + 1) if clean(n)]
        if not ok:
            raise SystemExit(f"spread {i}: no theme background is plain under its titles")
        n = min(ok, key=lambda n: np.abs(theme_patch(n, full, single).reshape(-1, 3).mean(0) - cur).sum())
        L["spreads"][i]["bg"] = n
        report.append(f"spread {i}: theme background {LIVE_BG[i]:02d} has a drawing under the title -> {n:02d}")
    for m in measured:
        no = m["page"] - getattr(C, "OFF", 1)
        i = 0 if no == 1 else no // 2
        sp = L["spreads"][i]
        sp["title"] = ""  # Lupa's own title is no longer used on this spread
        fx, fy, s = page_map(sp, plan_pages, no)
        for t in m["titles"]:
            px = t["fs"] * s  # font size in Lupa px (same scale as the photos)
            textured = any(g.get("texture") for g in sp["frames"])
            if textured:  # a little larger on a texture background – as long as it stays clear of photos and QRs
                xr = fx(t["x"] + t["w"]); cy0 = SH - TITLE_CY if t["bottom"] else TITLE_CY
                for sc in (1.2, 1.1, 1.0):
                    est = (xr - t["w"] * s * sc - px * 0.5, cy0 - px * sc * 1.1, xr + px * 0.5, cy0 + px * sc * 1.1)
                    if not any(hits(est, frame_box(f)) for f in sp["frames"] if not (f.get("bleed") and f["w"] >= HALF - 2)):
                        break
                px *= sc
            # horizontal: same alignment as the plan (right edge for Hebrew, left edge for English pages too:
            # the plan aligns every title to the right edge of its text box)
            x1 = fx(t["x"] + t["w"])
            cy = SH - TITLE_CY if t["bottom"] else TITLE_CY
            # theme or photo under it -> ink + background
            probe = (x1 - t["w"] * s - 40, cy - px, x1 + 40, cy + px)
            kind, crop = background(sp, path_of, probe)
            single = sp["type"] != "LAYFLAT_TYPE"
            bg_n = sp.get("bg") or LIVE_BG[i]
            if kind == "theme":
                col = theme_patch(bg_n, probe, single).reshape(-1, 3).mean(0)
                lum = float(col @ [0.299, 0.587, 0.114])
            else:
                lum = float((np.asarray(crop, float).reshape(-1, 3) @ [0.299, 0.587, 0.114]).mean())
            ink = "dark" if lum > 140 else "light"
            up = max(2, min(8, int(15000 / (t["w"] * s + 2 * px))))  # Chrome draws up to ~16000 px wide
            text = render_text(t["text"], px, ink, bool(t["ltr"]), up, strong=textured)
            tw, th = text.width / up, text.height / up  # Lupa px
            pad = round(px * 0.35)
            padv = max(px * 0.45 if textured else 4, (MIN_PX / up - th) / 2 + 1)  # room for the glow to fade out fully  # tall enough for Lupa's 800 px minimum
            box = (round(x1 - tw - pad), round(cy - th / 2 - padv), round(x1 + pad), round(cy + th / 2 + padv))
            x_lo, x_hi = (HALF - 1, SW) if (not single and no % 2 == 0) else (0, HALF)
            if box[2] > x_hi - SAFE:  # keep inside the safe area
                d = box[2] - (x_hi - SAFE); box = (box[0] - d, box[1], box[2] - d, box[3])
            if box[0] < x_lo + SAFE:
                d = x_lo + SAFE - box[0]; box = (box[0] + d, box[1], box[2] + d, box[3])
            for f in sp["frames"]:
                if f.get("bleed") and f["w"] >= HALF - 2:
                    continue  # the background itself
                if hits(box, frame_box(f)):
                    raise SystemExit(f"page {m['page']}: title '{t['text']}' would touch {'QR' if f['n'] == 0 else '#' + str(f['n'])}")
            kind, crop = background(sp, path_of, box)
            if kind == "theme":
                tile = Image.new("RGB", ((box[2] - box[0]) * up, (box[3] - box[1]) * up), tuple(int(round(v)) for v in theme_patch(bg_n, box, single).reshape(-1, 3).mean(0)))
            else:
                tile = crop.resize(((box[2] - box[0]) * up, (box[3] - box[1]) * up), Image.BICUBIC)
            tile = tile.convert("RGBA")
            tile.alpha_composite(text, (tile.width - pad * up - text.width, round((tile.height - text.height) / 2)))
            assert min(tile.size) >= MIN_PX, (out_name := t["text"], tile.size)
            sec = zlib.crc32(f"{t['text']}|{int(textured)}".encode()) % 7200
            while sec in taken:  # rare clash between two titles: next free second
                sec = (sec + 1) % 7200
            taken.add(sec)
            out = f"ready/upload/title_p{m['page']:03d}_{sec:04d}.jpg"
            # texture-spread titles got a wider glow margin (09.10 v2): a new time so Lupa sees them as new photos
            U.save_with_time(tile.convert("RGB"), out, t0 + timedelta(seconds=sec), quality=95)
            sp["frames"].append({"n": 0, "k": LL.key_of(out), "x": round((box[0] + box[2]) / 2),
                                 "y": round((box[1] + box[3]) / 2), "w": box[2] - box[0], "h": box[3] - box[1],
                                 "bleed": True, "title_tile": True, "text": t["text"]})
            count += 1
    # QR codes on a theme background: re-made with the theme colour as their background (no cream square)
    qr_of = {LL.key_of(q["file"]): q for q in C.QR_CODES}
    for f in glob.glob("ready/upload/lqr_*.jpg"):
        os.remove(f)
    jobs = []
    for i, sp in enumerate(L["spreads"]):
        single = sp["type"] != "LAYFLAT_TYPE"
        for f in sp["frames"]:
            textured = any(g.get("texture") for g in sp["frames"])
            kind, crop = background(sp, path_of, frame_box(f))
            if is_qr(f) and f["k"] in qr_of and (kind == "theme" or textured) and on_photo(sp, f) < 0.5:
                if kind == "theme":
                    col = tuple(int(round(v)) for v in theme_patch(sp.get("bg") or LIVE_BG[i], frame_box(f), single).reshape(-1, 3).mean(0))
                else:  # on a texture background: its average colour (a light plate if dark – scanners need contrast)
                    col = tuple(int(round(v)) for v in np.asarray(crop, float).reshape(-1, 3).mean(0))
                q = qr_of[f["k"]]
                out = f"ready/upload/lqr_p{q['page'] + 1:03d}_{len(jobs):02d}.jpg"
                d = re.search(r"(\d{4})-(\d{2})-(\d{2})", q["src"]).groups()  # fixed per QR: 2001 + its own month/day/"t"
                jobs.append((q["src"], out, [int(d[1]), int(d[2]), q.get("t", 30)], col, f))
    if jobs:
        code = ("import sys,json\nA=sys.argv[1]\nfrom datetime import datetime,timedelta\nimport make_qr as Q\n"
                "for src,out,k,col in json.loads(A):\n"
                "    Q.prepare(src,out,datetime(2001,1,2,8,0,0)+timedelta(seconds=(k[0]*31+k[1])*60+k[2]),tuple(col))\n")
        subprocess.run([QR_PY, "-c", code, json.dumps([j[:4] for j in jobs])], check=True)
        for src, out, k, col, f in jobs:
            f["k"] = LL.key_of(out)
            report.append(f"QR {out}: background {col} (theme colour, spread page)")
    # QR codes on top again (painted last)
    for s in L["spreads"]:
        s["frames"] = [f for f in s["frames"] if not f.get("title_tile") and not (f.get("bleed") and f["n"] == 0 and f["w"] < HALF - 2)] + \
                      [f for f in s["frames"] if f.get("title_tile")] + \
                      [f for f in s["frames"] if not f.get("title_tile") and f.get("bleed") and f["n"] == 0 and f["w"] < HALF - 2]
    json.dump(L, open("ready/lupa_layout.json", "w"), indent=0)
    print(f"{count} title images on {len(measured)} pages")
    print("\n".join(report))


if __name__ == "__main__":
    main()
