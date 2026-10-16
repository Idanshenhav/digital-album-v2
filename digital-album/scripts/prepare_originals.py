"""Download the full-size originals of every kept photo and apply its print tuning.

Usage (album folder, after build_plan.py + layout_pages.py):  python3 prepare_originals.py
Writes ready/photos/<page>_<photo#>.jpg (quality 95, sRGB) — page first so a folder upload keeps book order —
and ready/photos/index.json. Originals are cached in originals/ so re-runs only re-tune.
Tuning = brightness / contrast / saturation in percent from plan.json (same values as the HTML preview).
"""
import json
import math
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import numpy as np
from PIL import Image, ImageEnhance, ImageOps
import sys

sys.path.insert(0, os.getcwd())
try:
    from album_config import EXTRA_TUNE  # {photo#: {"shadows": 0-120, optional "bright"/"contrast"/"sat" overrides}} from review
except ImportError:
    EXTRA_TUNE = {}


def lift_shadows(im: Image.Image, amount: float, region: tuple | None = None) -> Image.Image:
    """Dodge: brighten shaded areas only (faces in shade), optionally only inside a soft region
    (x0, y0, x1, y1 as fractions of the photo), leaving sky, cliffs and highlights alone. amount 0-100."""
    from PIL import ImageFilter
    a = np.asarray(im, dtype=np.float32) / 255
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    shade = np.clip(1 - lum / 0.5, 0, 1) ** 0.8  # 1 in deep shade, 0 from mid-tones up
    if region:
        h, w = lum.shape
        m = Image.new("L", (w, h), 0)
        from PIL import ImageDraw
        x0, y0, x1, y1 = region
        ImageDraw.Draw(m).ellipse([x0 * w, y0 * h, x1 * w, y1 * h], fill=255)
        m = m.filter(ImageFilter.GaussianBlur(radius=0.06 * w))
        shade = shade * (np.asarray(m, dtype=np.float32) / 255)
    shade = np.asarray(Image.fromarray((shade * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(radius=3)), dtype=np.float32) / 255
    gain = 1 + (amount / 100) * 1.2 * shade
    out = np.clip(a * gain[..., None], 0, 1)
    return Image.fromarray((out * 255).astype(np.uint8))


def level(im: Image.Image, deg: float) -> Image.Image:
    """Rotate by deg and crop the largest centred rectangle of the original aspect with no empty corners."""
    w, h = im.size
    r = math.radians(abs(deg))
    k = 1 / (math.cos(r) + max(w / h, h / w) * math.sin(r))  # scale that keeps the corners inside
    out = im.rotate(deg, resample=Image.BICUBIC, expand=False)
    cw, ch = w * k, h * k
    return out.crop((round((w - cw) / 2), round((h - ch) / 2), round((w + cw) / 2), round((h + ch) / 2)))


def fetch(p: dict) -> str:
    """Original file (=d keeps full resolution)."""
    path = f"originals/{p['n']:03d}.jpg"
    if not os.path.exists(path) or os.path.getsize(path) < 50_000:
        subprocess.run(["curl", "-s", "-o", path, p["url"] + "=d"], timeout=300)
    return path


def tune(p: dict, src: str) -> str:
    """Apply the plan's tuning and save the print file."""
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    extra = EXTRA_TUNE.get(p["n"], {})
    if extra.get("rotate"):  # straighten (degrees, + = counter-clockwise), then trim the tilted edges, same aspect
        im = level(im, extra["rotate"])
    t = {**p["tune"], **{k: v for k, v in extra.items() if k in ("bright", "contrast", "sat")}}  # review overrides
    if extra.get("shadows"):  # lift shade first, so the contrast step doesn't push faces back down
        im = lift_shadows(im, extra["shadows"], extra.get("region"))
    im = ImageEnhance.Brightness(im).enhance(1 + t["bright"] / 100)
    im = ImageEnhance.Contrast(im).enhance(1 + t["contrast"] / 100)
    im = ImageEnhance.Color(im).enhance(1 + t["sat"] / 100)
    out = f"ready/photos/{p['page'] or 0:03d}_{p['n']:03d}.jpg"  # page 0 = cover only
    im.save(out, "JPEG", quality=95, subsampling=0)
    return out


def main() -> None:
    """All kept photos, in parallel."""
    os.makedirs("originals", exist_ok=True)
    os.makedirs("ready/photos", exist_ok=True)
    plan = json.load(open("plan.json"))
    keep = [p for p in plan["photos"] if p["keep"]]
    if "--only" in sys.argv:
        only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
        keep = [p for p in keep if p["n"] in only]
    with ThreadPoolExecutor(8) as ex:
        srcs = list(ex.map(fetch, keep))
    with ThreadPoolExecutor(6) as ex:
        outs = list(ex.map(lambda a: tune(*a), zip(keep, srcs)))
    old = {i["n"]: i for i in json.load(open("ready/photos/index.json"))} if os.path.exists("ready/photos/index.json") else {}
    for p, o in zip(keep, outs):
        old[p["n"]] = {"n": p["n"], "page": p["page"], "file": o, "w": Image.open(o).width, "h": Image.open(o).height}
    index = sorted(old.values(), key=lambda i: (i["page"] or 0, i["n"]))
    json.dump(index, open("ready/photos/index.json", "w"), indent=1)
    small = [i for i in index if max(i["w"], i["h"]) < 2000]
    print(f"{len(index)} print files in ready/photos; low-resolution originals: {[(i['n'], i['w'], i['h']) for i in small]}")


if __name__ == "__main__":
    main()
