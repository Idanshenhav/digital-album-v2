"""Extra upload files for the Lupa hybrid route (run after make_upload_set.py; only writes what is missing or changed).

- Full-page spreads: one background per open spread = the full-page photo + its blur running across BOTH pages.
  The facing page's photos are placed on top of it in Lupa as separate frames (so the blur continues behind them).
- The cover photo (plain, tuned) for Lupa's cover.
- Text halves (TEXT_HALF): a text card image, since Lupa's online editor has no free text boxes.
- Any kept photo that has no upload file yet (new picks since the last upload).
Every file gets a unique EXIF time, so lupa_layout.py can find it again among Lupa's renamed uploads.
"""
import glob
import os
import re
import sys
from datetime import timedelta

sys.argv = [sys.argv[0], "--no-symbols", "--no-cover-text"]
import render_spreads as R  # noqa: E402
from chrome import CHROME, TS  # noqa: E402
sys.argv = [sys.argv[0]]
import make_upload_set as U  # noqa: E402
from PIL import Image  # noqa: E402

import album_config as C  # noqa: E402


def have(n: int, tag: str) -> str | None:
    """Existing upload file for photo n with this tag ('' = the photo itself)."""
    pat = f"ready/upload/*_n{n:03d}{'_' + tag if tag else ''}.jpg"
    fs = [f for f in glob.glob(pat) if tag or not re.search(r"_n\d{3}_", os.path.basename(f))]
    return fs[0] if fs else None


def main() -> None:
    """Write the missing files."""
    pages, photos = R.PAGES, R.PHOTOS
    order = sorted((q for q in photos.values() if q["keep"] and q["page"]), key=lambda q: (q["page"], q["album_order"]))
    made = []
    # 1) photos without an upload file
    for k, p in enumerate(order):
        n = p["n"]
        if not have(n, "") and not any(pg["kind"] in ("hero", "spread") and n in pg["photos"] for pg in pages):
            im = Image.open(R.FILES[n]).convert("RGB")
            im.thumbnail((3000, 3000), Image.LANCZOS)
            out = f"ready/upload/{p['page']:03d}_{k:03d}_n{n:03d}.jpg"
            U.save_with_time(im, out, U.stamp(p), quality=87)
            made.append(out)
    # 2) full page + facing page -> one background across the spread
    for i in range(1, len(pages) // 2):
        right, left = pages[2 * i - 1], pages[2 * i]
        for hero, face in ((right, left), (left, right)):
            if hero["kind"] == "hero" and face["kind"] in ("photos", "text", "closing"):
                n = hero["photos"][0]
                if have(n, "herospread"):
                    continue
                bare = dict(face, kind="photos", rects=[], merged=False)
                r2, l2 = (hero, bare) if hero is right else (bare, hero)
                nm, html, W = R.build_opening(800 + i, r2, l2)
                when = U.stamp(photos[n]) + timedelta(seconds=3)
                jpg = R.shoot(800 + i, nm, html, W, when)
                out = f"ready/upload/{hero['no']:03d}_herospread_n{n:03d}_herospread.jpg"
                U.save_with_time(Image.open(jpg).convert("RGB"), out, when, quality=90)
                os.remove(jpg)
                made.append(out)
    # 3) cover photo
    if getattr(C, "COVER_ONLY", False) and not os.path.exists("ready/upload/000_cover.jpg"):
        p = photos[C.COVER]
        im = Image.open(R.FILES[C.COVER]).convert("RGB")
        im.thumbnail((3600, 3600), Image.LANCZOS)
        U.save_with_time(im, "ready/upload/000_cover.jpg", U.stamp(p) + timedelta(seconds=5), quality=92)
        made.append("ready/upload/000_cover.jpg")
    # 4) text halves as text cards (13.6 x 18.6 cm)
    for sec, th in getattr(C, "TEXT_HALF", {}).items():
        out = f"ready/upload/textcard_{sec}.jpg"
        if os.path.exists(out):
            continue
        pg = next(p for p in pages if p.get("textbox") and p["sec"] == sec)
        html = f"""<!doctype html><html dir="rtl"><head><meta charset="utf-8"><style>
html,body{{margin:0;width:1606px;height:2197px;background:#faf6ee;font-family:"SF Hebrew","Arial Hebrew",Arial}}
div{{box-sizing:border-box;padding:170px 130px;color:#2c2a26;font-size:62px;line-height:1.65;text-align:right}}
b{{display:block;font-size:96px;margin-bottom:60px}}</style></head><body><div><b>{th['title']}</b>{th['text']}</div></body></html>"""
        path = os.path.abspath(f"ready/render/textcard_{sec}.html")
        open(path, "w").write(html)
        png = os.path.abspath(f"ready/render/textcard_{sec}.png")
        os.system(f'{TS(90)}"{CHROME}" --headless=new --disable-gpu '
                  f'--hide-scrollbars --user-data-dir="{os.path.abspath("ready/render/.chr")}" --window-size=1606,2197 '
                  f'--screenshot="{png}" "file://{path}" >/dev/null 2>&1')
        when = U.stamp(photos[pg["photos"][0]]) + timedelta(seconds=7)
        U.save_with_time(Image.open(png).convert("RGB"), out, when, quality=92)
        made.append(out)
    print(len(made), "new upload files:", *made, sep="\n  ")


if __name__ == "__main__":
    main()
