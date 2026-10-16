"""Front cover with the title drawn into the photo (bold, white, soft shadow), on the sky.

Album editors' cover text usually offers a thin font with no bold and no shadow, so the title goes into the photo:
plan font, weight 800, two lines (COVER_TITLE_HE / COVER_SUB_HE in album_config.py, any language).
Keep it on the sky, off faces and mountain tops, at least 0.5 cm inside the trim. Settings (album_config.py):
COVER_PHOTO_FILE, COVER_TITLE_FILE, COVER_TITLE_CX, COVER_TITLE_FONT, COVER_TITLE_STAMP (new seconds = new photo
for the editor). The cover-sheet numbers below are Lupa Panoramic Large; check them for another book.

Usage (album folder):  python3 make_cover_title.py
"""
import html
import subprocess
import tempfile
from datetime import datetime

from PIL import Image

import album_config as C
import make_upload_set as U

from chrome import CHROME, T
SRC = getattr(C, "COVER_PHOTO_FILE", "ready/upload/000_cover.jpg")  # the tuned cover photo, cut to the cover shape
OUT = getattr(C, "COVER_TITLE_FILE", "ready/upload/000_cover_title.jpg")
# Lupa cover sheet: front photo frame 3720 x 2811 px at (0,0), trimmed X 0.015 / W 0.97083 of the photo
FRAME_W, FRAME_H, CROP_X, CROP_W = 3720, 2811, 0.015, 0.97083336
BLEED, SAFE = 118, 59  # cover bleed, then 0.5 cm
CX = getattr(C, "COVER_TITLE_CX", 1450)  # title centre on the cover sheet (px): put it on the sky, off faces and peaks
FONT = getattr(C, "COVER_TITLE_FONT", 207)  # px on the cover sheet; the second line is half of it


def main() -> None:
    im = Image.open(SRC).convert("RGB")
    k = CROP_W * im.width / FRAME_W  # photo px per cover-sheet px
    fs = FONT * k
    sh = fs / 36  # plan shadow 0 2px 10px at 36 px
    page = (f"<html><body style='margin:0;background:transparent'><div dir='rtl' style='display:inline-block;padding:{fs:.0f}px;"
            f"text-align:center;color:#fff;font-family:-apple-system,system-ui,\"Segoe UI\",Heebo,Arial,sans-serif;"
            f"font-weight:800;font-size:{fs:.1f}px;line-height:1.05;text-shadow:0 {2 * sh:.1f}px {10 * sh:.1f}px rgba(0,0,0,.55)'>"
            f"{html.escape(C.COVER_TITLE_HE)}<small style='display:block;font-weight:600;font-size:.5em;margin-top:0'>"
            f"{html.escape(C.COVER_SUB_HE)}</small></div></body></html>")
    with tempfile.TemporaryDirectory() as d:
        open(f"{d}/c.html", "w", encoding="utf8").write(page)
        subprocess.run([*T(60), CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars",
                        "--default-background-color=00000000", f"--window-size={int(fs * 12)},{int(fs * 5)}",
                        f"--screenshot={d}/c.png", f"file://{d}/c.html"], capture_output=True, check=True)
        txt = Image.open(f"{d}/c.png").convert("RGBA")
    a = txt.getchannel("A")
    glyphs = a.point(lambda v: 255 if v > 200 else 0).getbbox()  # the letters themselves (not the shadow)
    txt = txt.crop(a.point(lambda v: 255 if v > 3 else 0).getbbox())
    g_top = glyphs[1] - a.point(lambda v: 255 if v > 3 else 0).getbbox()[1]
    x = round(CROP_X * im.width + CX * k - txt.width / 2)
    y = round((BLEED + SAFE) * im.height / FRAME_H - g_top)  # first letter top = 0.5 cm under the trim
    out = im.convert("RGBA")
    out.alpha_composite(txt, (x, max(0, y)))
    U.save_with_time(out.convert("RGB"), OUT, getattr(C, "COVER_TITLE_STAMP", datetime(2001, 1, 3, 8, 0, 0)), quality=95)  # bump the stamp's seconds on every re-make
    print(OUT, "title box", x, y, txt.size)


if __name__ == "__main__":
    main()
