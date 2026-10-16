# QR codes on album pages

A QR code on a page opens the videos or extra photos of that place. Offer one per place that has a video album.

## 1. Get the link and the name
- Ask the user for each link (a Google Photos album or set, or a Google Drive file). Keep the exact URL.
- Name the file from the linked item's own **date taken + place taken** (its Info / Details panel in Google
  Photos or Drive): `YYYY-MM-DD_<place-slug>.jpg`. Never use the album name or upload date. For a set, use one
  representative item and say which. Missing date or place: ask. Never overwrite; add `-02`.

## 2. Make the code
"""
python3 scripts/create_qr.py --url "<URL>" --date YYYY-MM-DD --location "Place" --output-root .
"""
- Cream background, deep green rounded dots, lightly rounded corners and finder squares (strong rounding failed
  scan tests). High error correction, standard quiet zone. No captions.
- Writes `qr-codes/<name>.jpg` + a `.png` with see-through corners. It scans each file at full size and at 2 cm
  and stops with SCAN FAILED otherwise. Show the JPEG to the user.

## 3. Place it
- **Size:** at least 2 cm printed (1.3 cm failed). 2.34 cm is a good default.
- **Where:** on background (sky, ground, plain wall, margin, the blurred strip of a full page), small, near an edge
  or corner, at least 0.5 cm from the trim. **Never on faces** or the main subject. Show the spot before placing.
- **Layering (rule from the printed book):** the QR is the **top layer** of its page, above photos, titles and
  frame lines, and it must **never straddle a photo's edge**. Either fully outside every photo with 0.3 cm clear
  space, or fully inside one photo at least 0.3 cm from its edges. Album editors can draw a photo's frame line on
  top of everything, so a QR crossing a photo edge printed with a line through it.
- **No frame line around the QR:** in Lupa `m_folder_frame = {m_width_px: 8, m_frame_opacity: 0}` (width 0 gives
  the theme's dark line; only opacity 0 hides it). lupa_apply.js does this for every QR.
- **Colour:** `make_qr.py` tints the code's light part to the page colour under it (`bg`), so no cream square shows.
  On dark pages it keeps a light plate with dark dots (scanners need contrast). On busy textures a plain square is
  needed for scanning; that is fine.
- Config entry (album_config.py `QR_CODES`): file, src, bg, t (unique EXIF second), page, x, y, s (cm), note.
  A Lupa-only position can be forced with `"lupa": (x_px, y_px)` (centre on the spread).

## 4. Check
- `python3 check_book.py` must show no QR errors (size, trim, top layer, straddling).
- In the editor: `claudeLupa.check()` → `qrNotOnTop` and `qrCrossesPhoto` empty. Look at a zoomed screenshot.
- Scan the code on the screen with a phone if the user can.
