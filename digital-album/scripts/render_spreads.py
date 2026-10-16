"""Render every open spread of the plan as one print-ready image for Lupa (Dutch book, lay-flat).

Usage (album folder, after prepare_originals.py):  python3 render_spreads.py [--only 12,13]
Output: ready/spreads/NN_pAAA-BBB.jpg — 60 x 22 cm at 300 dpi (7087 x 2598 px); page 1 and the last page are
single 30 x 22 cm images (3543 x 2598 px). Photos sit in their exact plan frames, blur fills run across
the facing page, Hebrew titles + symbols are drawn by headless Chrome (PIL can't lay out Hebrew).
Files carry sequential EXIF dates so Lupa keeps them in book order.
"""
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from html import escape

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

sys.path.insert(0, os.getcwd())
import album_config as C  # noqa: E402

DPI = 300
CM = DPI / 2.54
PW, PH = 30.0, 22.0
from chrome import CHROME
HERE = os.getcwd()

plan = json.load(open("plan.json"))
PAGES = plan["pages"]
SEC = plan["sections"]
PHOTOS = {p["n"]: p for p in plan["photos"]}
FILES = {i["n"]: os.path.abspath(i["file"]) for i in json.load(open("ready/photos/index.json"))}
EMO = json.load(open("symbols/emoji/map.json")) if os.path.exists("symbols/emoji/map.json") else {}
used_sym: set[str] = set()


def px(cm: float) -> str:
    """cm -> css px at print resolution."""
    return f"{cm * CM:.1f}px"


def blur_file(n: int, w_cm: float, h_cm: float) -> str:
    """Blurred, cover-cropped copy of photo n for a w x h cm area (small file; Chrome scales it up smoothly)."""
    out = f"ready/blur/{n:03d}_{int(w_cm)}x{int(h_cm)}.jpg"
    if not os.path.exists(out):
        os.makedirs("ready/blur", exist_ok=True)
        im = Image.open(FILES[n]).convert("RGB")
        im = ImageOps.fit(im, (int(w_cm * 30), int(h_cm * 30)))  # ~30 px per cm is plenty once blurred
        im = im.filter(ImageFilter.GaussianBlur(radius=im.width * 0.025))
        im = ImageEnhance.Brightness(im).enhance(0.92)
        im = ImageEnhance.Color(im).enhance(1.1)
        im.save(out, quality=88)
    return os.path.abspath(out)


def symbol_once(sec: str) -> str:
    """The place's symbol, the first time the place gets a title (same rule as the HTML plan)."""
    if "--no-symbols" in sys.argv or sec not in EMO or sec in used_sym or not os.path.exists(f"symbols/emoji/{sec}.png"):
        return ""
    used_sym.add(sec)
    return f"<img class='sym' src='file://{os.path.abspath(f'symbols/emoji/{sec}.png')}'>"


def title_div(text: str, right_cm: float, sym: str = "", on_blur: bool = False) -> str:
    """Page title at the top, its right edge at right_cm (canvas coords)."""
    return (f"<div class='ttl{' onblur' if on_blur else ''}' style='right:calc(var(--W) - {px(right_cm)});top:{px(0.7)}'>"
            f"{sym}<span>{escape(text)}</span></div>")


def img(n: int, x: float, y: float, w: float, h: float) -> str:
    """One photo frame (object-fit cover = the plan's ≤5% trim)."""
    return f"<img class='ph' src='file://{FILES[n]}' style='left:{px(x)};top:{px(y)};width:{px(w)};height:{px(h)}'>"


def page_items(pg: dict, off: float, facing: dict | None) -> tuple[str, str]:
    """(background html, foreground html) for one page placed at x offset `off` cm."""
    bg, fg = "", ""
    kind = pg["kind"]
    shared = None
    if facing is not None:
        for a, b in ((pg, facing), (facing, pg)):
            if a["kind"] == "hero" and b["kind"] in ("photos", "text", "closing"):
                shared = a["photos"][0]
    if kind in ("hero", "title"):
        r = pg["rects"][0]
        if not shared:
            bg += f"<div class='bg' style='left:{px(off)};width:{px(PW)};background-image:url(&quot;file://{blur_file(r['n'], PW, PH)}&quot;)'></div>"
        fg += img(r["n"], off + r["x"], r["y"], r["w"], r["h"])
        if kind == "title" and "--no-cover-text" not in sys.argv:
            fg += (f"<div class='cover' style='left:{px(off)};width:{px(PW)}'>{escape(C.COVER_TITLE_HE)}"
                   f"<small>{escape(C.COVER_SUB_HE)}</small></div>")
    elif kind == "opening":
        fg += (f"<div class='intro opening' style='left:{px(off + 4)};top:{px(3.5)};width:{px(PW - 8)};height:{px(15)}'>"
               f"<b>{escape(C.OPENING_TITLE_HE)}</b>{escape(C.OPENING_TEXT_HE)}<i>{escape(C.OPENING_SIGN_HE)}</i></div>")
    elif kind == "map":
        fg += f"<img class='ph' src='file://{os.path.abspath('map/route_map.png')}' style='left:{px(off)};top:0;width:{px(PW)};height:{px(PH)}'>"
    elif kind in ("text", "closing"):
        # divider / closing page: blur of a neighbouring big photo + one line of text
        n = shared or next((p["photos"][0] for p in PAGES[pg["no"]:] if p["kind"] in ("spread", "hero")), None) \
            or next(p["photos"][0] for p in reversed(PAGES[:pg["no"]]) if p["photos"])
        if not shared:
            bg += f"<div class='bg' style='left:{px(off)};width:{px(PW)};background-image:url(&quot;file://{blur_file(n, PW, PH)}&quot;)'></div>"
        line = "סוף הדרך… עד הטיול הבא" if kind == "closing" else SEC[pg["secs"][0]]["he"]
        fg += f"<div class='divider' style='left:{px(off)};width:{px(PW)}'>{escape(line)}</div>"
    elif pg.get("rects") and not pg.get("merged"):
        for r in pg["rects"]:
            fg += img(r["n"], off + r["x"], r["y"], r["w"], r["h"])
        secs = pg.get("secs") or [pg["sec"]]
        sym = ""
        for s in secs:
            sym = sym or symbol_once(s)
        fg += title_div(" · ".join(SEC[s]["he"] for s in secs)[:45], off + PW - 1.0, sym, bool(shared))
    return bg, fg, shared


def build_opening(i: int, right: dict | None, left: dict | None) -> tuple[str, str, float]:
    """(file name, html, width cm) for one opening. Runs in book order so symbols are claimed in order."""
    single = right is None or left is None
    W = PW if single else 2 * PW
    bg = fg = ""
    shared_bg = None
    pages = [(left, 0.0), (right, 0.0 if single else PW)] if not single else [((left or right), 0.0)]
    merged = (not single) and right.get("merged")
    for pg, off in pages:
        if pg is None:
            continue
        facing = None if single else (right if pg is left else left)
        b, f, sh = page_items(pg, off, facing)
        bg += b
        fg += f
        shared_bg = shared_bg or sh
    if merged:
        for r in right["rects"]:
            fg += img(r["n"], r["x"], r["y"], r["w"], r["h"])
        if right["kind"] == "intro":
            fg += title_div(C.INTRO_TITLE_HE, 2 * PW - 1.0, symbol_once(right["sec"]))
            if getattr(C, "INTRO_TEXT_BOX", True):
                fg += (f"<div class='intro' style='left:{px(48.8)};top:{px(2.4)};width:{px(10.2)};height:{px(18.6)}'>"
                       f"<b>{escape(C.INTRO_TITLE_HE)}</b>{escape(C.INTRO_TEXT_HE)}</div>")
        else:
            th = getattr(C, "TEXT_HALF", {}).get(left["sec"]) if left.get("textbox") else None
            if th:
                fg += (f"<div class='intro' style='left:{px(1.0)};top:{px(2.4)};width:{px(13.6)};height:{px(18.6)}'>"
                       f"<b>{escape(th['title'])}</b>{escape(th['text'])}</div>")
            for t in right["titles"]:
                rr = min(t["right"], 29.3) if t["right"] <= 36 else t["right"]  # a title near the fold goes on the left page
                fg += title_div(" · ".join(SEC[s]["he"] for s in t.get("secs", [t["sec"]]))[:45], rr, symbol_once(t["sec"]))
    for pg in (right, left):
        if pg is not None and pg["kind"] == "spread" and pg.get("half") == "right":
            r = pg["rects"][0]
            bg += f"<div class='bg' style='left:0;width:{px(W)};background-image:url(&quot;file://{blur_file(r['n'], 2 * PW, PH)}&quot;)'></div>"
            fg = img(r["n"], r["x"], r["y"], r["w"], r["h"])
    if shared_bg:
        bg = f"<div class='bg' style='left:0;width:{px(W)};background-image:url(&quot;file://{blur_file(shared_bg, W, PH)}&quot;)'></div>" + bg
    nos = [p["no"] for p in (right, left) if p is not None]
    name = f"{i:02d}_p{min(nos):03d}" + ("" if single else f"-{max(nos):03d}")
    html = f"""<!doctype html><html dir="rtl"><head><meta charset="utf-8"><style>
:root{{--W:{px(W)}}}
html,body{{margin:0;width:{px(W)};height:{px(PH)};overflow:hidden;background:#fff;font-family:"SF Hebrew","Arial Hebrew",Arial,sans-serif}}
.bg{{position:absolute;top:0;height:{px(PH)};background-size:cover;background-position:center}}
.ph{{position:absolute;object-fit:cover;box-shadow:0 {px(0.05)} {px(0.25)} rgba(0,0,0,.25)}}
.ttl{{position:absolute;display:flex;align-items:center;gap:{px(0.25)};font-weight:700;font-size:{px(0.62)};color:#1f2328;white-space:nowrap;direction:rtl}}
.ttl.onblur{{background:rgba(255,255,255,.82);padding:{px(0.1)} {px(0.35)};border-radius:{px(0.3)}}}
.sym{{height:{px(1.05)};width:{px(1.05)}}}
.cover{{position:absolute;top:{px(1.1)};text-align:center;color:#fff;font-weight:800;font-size:{px(1.9)};line-height:1.05;text-shadow:0 {px(0.08)} {px(0.4)} rgba(0,0,0,.55)}}
.cover small{{display:block;font-weight:600;font-size:.5em;margin-top:{px(0.2)}}}
.divider{{position:absolute;top:{px(9.5)};text-align:center;color:#fff;font-weight:800;font-size:{px(1.5)};text-shadow:0 {px(0.08)} {px(0.4)} rgba(0,0,0,.5)}}
.intro.opening{{background:rgba(255,255,255,.82);font-size:{px(0.62)};display:flex;flex-direction:column;justify-content:center;text-align:center}}
.intro.opening b{{font-size:{px(1.3)}}} .intro.opening i{{display:block;margin-top:{px(0.6)};font-style:normal;color:#666}}
.intro{{position:absolute;box-sizing:border-box;padding:{px(0.6)};font-size:{px(0.5)};line-height:1.6;color:#333;text-align:right;background:rgba(255,255,255,.7);border-radius:{px(0.3)}}}
.intro b{{display:block;font-size:1.4em;margin-bottom:{px(0.3)}}}
</style></head><body>{bg}{fg}</body></html>"""
    return name, html, W


def shoot(i: int, name: str, html: str, W: float, stamp: datetime) -> str:
    """Screenshot the html with headless Chrome and save the print JPEG."""
    os.makedirs("ready/render", exist_ok=True)
    os.makedirs("ready/spreads", exist_ok=True)
    hp, pp = f"ready/render/{name}.html", f"ready/render/{name}.png"
    open(hp, "w").write(html)
    wpx, hpx = round(W * CM), round(PH * CM)
    if os.path.exists(pp):
        os.remove(pp)
    # headless Chrome writes the screenshot quickly but often doesn't exit: wait for the file, then close it
    proc = subprocess.Popen([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                             f"--user-data-dir={HERE}/ready/render/.chr{i % 4}", f"--window-size={wpx},{hpx}", "--virtual-time-budget=8000",
                             "--allow-file-access-from-files", f"--screenshot={HERE}/{pp}", f"file://{HERE}/{hp}"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    import time
    t0, last = time.time(), -1
    while time.time() - t0 < 120:
        if proc.poll() is not None:
            break
        if os.path.exists(pp):
            size = os.path.getsize(pp)
            if size > 0 and size == last:
                break
            last = size
        time.sleep(1)
    proc.kill()
    proc.wait()
    im = Image.open(pp).convert("RGB").crop((0, 0, wpx, hpx))
    exif = Image.Exif()
    exif[0x0132] = stamp.strftime("%Y:%m:%d %H:%M:%S")  # DateTime
    exif.get_ifd(0x8769)[0x9003] = stamp.strftime("%Y:%m:%d %H:%M:%S")  # DateTimeOriginal -> book order
    out = f"ready/spreads/{name}.jpg"
    im.save(out, "JPEG", quality=92, subsampling=0, dpi=(DPI, DPI), exif=exif)
    os.remove(pp)
    return out


def main() -> None:
    """All openings: [page 1], (2,3) ... (98,99), [last page]."""
    only = set()
    if "--only" in sys.argv:
        only = {int(x) for x in sys.argv[sys.argv.index("--only") + 1].split(",")}
    openings = [(None, PAGES[0])] + [(PAGES[2 * k - 1], PAGES[2 * k]) for k in range(1, len(PAGES) // 2)] + [(PAGES[-1], None)]
    start = datetime(2021, 8, 9, 8, 0, 0)
    built = [(i, *build_opening(i, r, l), start + timedelta(minutes=i), r, l) for i, (r, l) in enumerate(openings)]
    todo = [b for b in built if not only or any(p is not None and p["no"] in only for p in (b[5], b[6]))]
    with ThreadPoolExecutor(3) as ex:
        outs = list(ex.map(lambda b: shoot(*b[:5]), todo))
    print(f"{len(outs)} images in ready/spreads")


if __name__ == "__main__":
    main()
