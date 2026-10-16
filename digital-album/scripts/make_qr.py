"""Prepare QR codes for the Lupa book so they show NO visible frame.

Usage (album folder):  python3 make_qr.py
For every entry in QR_CODES (album_config.py) it reads the source file ("src", from qr-codes/), and writes "file"
(ready/upload/qr_*.jpg):
- trimmed to the code, with a quiet zone of 2 modules (scanners need it)
- recolored: the light part becomes the PAGE BACKGROUND color ("bg" in the entry, default the theme teal
  174,219,214), the code becomes a deep dark color -> no white square, no frame, just the code on the page
- EXIF DateTimeOriginal = the date in the file name + 23:59:SS (unique second per entry), so lupa_layout.py can match
  it to Lupa's renamed upload
- checked: the code must still scan (OpenCV), at full size and at phone-distance size; otherwise the script stops.
In Lupa the QR frame must ALSO get an invisible line: m_folder_frame = {m_width_px: 8, m_frame_opacity: 0}
(width 0 = theme's dark line; '#00FFFFFF' is drawn white). lupa_apply.js does that for frames marked "bleed" (lupa_layout.py marks QR frames).
"""
import re
from datetime import datetime

import cv2
import numpy as np
from PIL import Image

import album_config as C
import make_upload_set as U

TEAL = getattr(C, "QR_DEFAULT_BG", (246, 243, 236))  # page colour under the code when an entry gives no "bg"
DARK = (28, 45, 42)


def prepare(src: str, out: str, when: datetime, bg: tuple = TEAL, dark: tuple = DARK) -> str:
    """Write the frameless QR and return what it scans to."""
    # A tinted QR is only safe when its modules remain clearly separated from
    # the page. On darker backgrounds, use a light quiet-zone plate instead of
    # allowing the dots and page tint to merge in print or on a phone camera.
    # The outer Lupa frame remains invisible; this is only the QR's scan-safe
    # quiet zone.
    if (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]) < 150:
        bg = (248, 247, 240)
        dark = (20, 24, 22)
    g = np.asarray(Image.open(src).convert("L"))
    ys, xs = np.where(g < 128)
    g = g[ys.min():ys.max() + 1, xs.min():xs.max() + 1]  # tight to the code (drops any caption / old margin)
    pad = round(g.shape[1] / 29 * 2)  # ~2 modules of quiet zone
    g = np.pad(g, pad, constant_values=255).astype(np.float32) / 255
    g = np.clip((g - 0.35) / 0.4, 0, 1)  # any light shade (old card / margin) becomes page background
    rgb = np.array(dark, np.float32) + (np.array(bg, np.float32) - np.array(dark, np.float32)) * g[..., None]
    im = Image.fromarray(rgb.clip(0, 255).astype(np.uint8)).resize((900, 900), Image.NEAREST)
    U.save_with_time(im, out, when, quality=95)
    img = cv2.imread(out)
    full = cv2.QRCodeDetector().detectAndDecode(img)[0]
    small = cv2.QRCodeDetector().detectAndDecode(cv2.resize(img, (200, 200), interpolation=cv2.INTER_AREA))[0]
    if not full or full != small:
        raise SystemExit(f"{out}: does not scan reliably ({full!r} / {small!r}) – use a cleaner source file")
    return full


def main() -> None:
    """All QR codes in QR_CODES."""
    for k, q in enumerate(getattr(C, "QR_CODES", [])):
        d = re.search(r"(\d{4})-(\d{2})-(\d{2})", q["src"]).groups()
        when = datetime(int(d[0]), int(d[1]), int(d[2]), 23, 59, q.get("t", 30 + k % 30))  # "t": new second for a re-made file
        url = prepare(q["src"], q["file"], when, tuple(q.get("bg", TEAL)), tuple(q.get("dark", DARK)))  # "dark": darker dots on a dark page
        print(f"{q['file']}  page {q['page'] + 1} (Lupa)  ->  {url}")


if __name__ == "__main__":
    main()
