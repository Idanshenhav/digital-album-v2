"""Build the upload set for designing the album INSIDE Lupa with a Lupa theme ("hybrid" route).

Usage (album folder, after prepare_originals.py):  python3 make_upload_set.py
- Photos on normal pages -> the tuned photo itself (long side ≤ 3600 px, JPEG q90), so Lupa's theme lays them out.
- Cover, full-page photos and double-page spreads -> ready images with the blurred fill built in
  (single page 30x22 cm or spread 60x22 cm at 300 dpi), to place as one borderless photo in the Dutch book.
Every file gets EXIF DateTimeOriginal = the photo's real time (camera clocks fixed) and a page-order file name,
so Lupa lines them up like the plan. Writes ready/upload/ and ready/upload/batches.json (≤ 9.5 MB per batch).
"""
import json
import os
import sys
from datetime import datetime, timezone

from PIL import Image

sys.argv = [sys.argv[0], "--no-symbols"]  # render_spreads: symbols are the last step
import render_spreads as R  # noqa: E402

MAX_SIDE = 3600
BATCH_BYTES = 9_500_000


def stamp(p: dict) -> datetime:
    """Photo's local time with the clock fixes applied (as used for the album order)."""
    return datetime.fromtimestamp((p["cts"] + (p["tz"] or 0)) / 1000, timezone.utc).replace(tzinfo=None)


def save_with_time(im: Image.Image, out: str, when: datetime, quality: int = 90) -> None:
    """JPEG with EXIF date so Lupa sorts it right."""
    exif = Image.Exif()
    t = when.strftime("%Y:%m:%d %H:%M:%S")
    exif[0x0132] = t
    exif.get_ifd(0x8769)[0x9003] = t
    im.save(out, "JPEG", quality=quality, subsampling=0, dpi=(300, 300), exif=exif)


def main() -> None:
    """Write the upload files and batches."""
    os.makedirs("ready/upload", exist_ok=True)
    pages = R.PAGES
    big = {}  # photo n -> ("page", pg) or ("spread", right_half, left_half)
    for i, pg in enumerate(pages):
        if pg["kind"] in ("hero", "title"):
            big[pg["photos"][0]] = ("page", pg)
        elif pg["kind"] == "spread" and pg.get("half") == "right":
            big[pg["photos"][0]] = ("spread", pg, pages[i + 1])
    files = []
    if os.path.exists("map/route_map.png") and not os.path.exists("ready/upload/003_map.jpg"):  # the route-map page
        save_with_time(Image.open("map/route_map.png").convert("RGB"), "ready/upload/003_map.jpg", datetime(2001, 1, 4, 8, 0, 0), quality=92)
    order = sorted((p for p in R.PHOTOS.values() if p["keep"] and p["page"]), key=lambda p: (p["page"], p["album_order"]))  # cover-only photos have no page
    for k, p in enumerate(order):
        n = p["n"]
        name = f"ready/upload/{p['page']:03d}_{k:03d}_n{n:03d}"
        if n in big:
            spec = big[n]
            if spec[0] == "page":
                nm, html, W = R.build_opening(900 + k, None, spec[1])
            else:
                nm, html, W = R.build_opening(900 + k, spec[1], spec[2])
            jpg = R.shoot(900 + k, nm, html, W, stamp(p))
            im = Image.open(jpg).convert("RGB")
            out = name + ("_fullpage.jpg" if spec[0] == "page" else "_spread.jpg")
            save_with_time(im, out, stamp(p), quality=90)
            os.remove(jpg)
        else:
            im = Image.open(R.FILES[n]).convert("RGB")
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
            out = name + ".jpg"
            save_with_time(im, out, stamp(p))
        files.append(out)
    batches, cur, size = [], [], 0
    for f in files:
        s = os.path.getsize(f)
        if cur and size + s > BATCH_BYTES:
            batches.append(cur)
            cur, size = [], 0
        cur.append(os.path.abspath(f))
        size += s
    if cur:
        batches.append(cur)
    json.dump(batches, open("ready/upload/batches.json", "w"), indent=1)
    total = sum(os.path.getsize(f) for f in files)
    print(f"{len(files)} files ({sum(1 for f in files if 'fullpage' in f)} full pages, {sum(1 for f in files if 'spread' in f)} spreads), "
          f"{total / 1e6:.0f} MB, {len(batches)} upload batches")


if __name__ == "__main__":
    main()
