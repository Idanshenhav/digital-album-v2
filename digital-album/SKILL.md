---
name: digital-album
description: Turn a shared Google Photos album of a trip into a printed photo book, end to end. It learns the trip (photo count, places, dates), researches the album maker's books, sales and vouchers, suggests the best book and theme, picks and enhances the best photos, builds an interactive HTML plan the user marks up, drives the album editor in the browser (fully automated for Lupa, guided for other makers), places QR codes for videos, and runs a final print check. Use it whenever someone wants a photo album, photo book, "אלבום", "ספר תמונות", "לופה" or a printed trip book, shares a photos.app.goo.gl / photos.google.com album link for a book, asks which album maker or deal is best, or continues work on an album folder ("page 42…", "swap 165 and 172", "straighten 328", "add a QR to page 12") — even if they never say "skill".
---

# Digital album: from a Google Photos link to a printed book

The user is usually not technical. Do all the technical work yourself, explain in plain words, show results
visually (the HTML plan, screenshots), and verify before saying something is done. End each reply with 2–3 short
next-step options. Ask only for decisions that are the user's: the book, the theme, the photos, the texts, the
price option. Never order, never add to cart, never enter passwords or payment details, decline non-essential
cookies. Edit nothing in the album editor before the user says go for that round.

Read before starting: `references/design-rules.md` (the look and the rules), then the reference for the stage.

## Stage 0 · Setup (first time on this computer)
Ask for (or create) one folder per album. Copy `scripts/*` and `assets/plan.css`, `assets/plan.js` into it, and
`assets/album_config_template.py` as `album_config.py`. Run the checks in `references/cowork-setup.md`.
Ask once: the book's text language (Hebrew or English titles; the book reads right to left either way).

## Stage 1 · Learn the trip from the album link
1. `python3 fetch_album.py "<link>"`: numbered photos (camera-time order), 600 px previews, contact sheets of
   20, sizes, cameras, quality stats. Report: photo count, dates, number of cameras, videos.
2. Review every photo with parallel subagents, all launched in one message, ~140 photos each, with
   `references/review_prompt.md` (they write `notes/part<N>.json`). Merge their places → SECTIONS in
   album_config.py (page title per place in the book's language, ≤45 characters).
3. `python3 clock_check.py` (needs the review notes): finds a camera whose clock was off (one is common). Put the
   fix in CLOCK_FIXES and tell the user in one line.
4. Locations: `references/locations.md` (the owner's signed-in Google Photos, or ask for the stops).
Show: the trip as a list of places with dates and photo counts.

## Stage 2 · Learn the album maker
Ask which company (suggest Lupa for Israel). For Lupa read `references/lupa.md`, for any other maker follow
`references/other-companies.md`. Check live: books, sizes, page limits, lay-flat, current sales, coupons and
vouchers (and whether they stack), shipping. Use a background subagent for the deal research while you work.
Show a price table with sources and the total for the likely page count.

## Stage 3 · Suggest the book and theme
- Page count from the photos: about 4–5 photos per page plus a full page every 5–7 pages; round to the maker's
  page step; at most the product's maximum.
- Shape from the photos (mostly landscape → panoramic). Lay-flat if there are drone shots or panoramas.
- 3–5 themes that fit the trip's look, with sample pictures in `themes/`, one marked as the top pick.
Write PRODUCT_HTML and THEMES in the config. The user decides.

## Stage 4 · Build the HTML plan
1. Fill album_config.py: SECTIONS, COVER, DEPARTURE, intro, texts, EXTRA_TUNE, STOPS/ROUTE.
2. `python3 build_plan.py && python3 layout_pages.py`, then `python3 prepare_originals.py` (full-size originals,
   print tuning, straightening), `python3 make_map.py`, `python3 make_html.py`.
3. Check: every kept photo framed once, every left-out photo has a reason, page count right, a big photo every
   5–7 pages, no crop beyond 5%.
4. Serve the folder on localhost (`python3 -m http.server <port> --bind 127.0.0.1`) and open the plan in the
   browser pane. Screenshot pages yourself before showing it. What the page has: `references/plan-page.md`.

## Stage 5 · Changes (as many rounds as the user wants)
Marks from the plan ("Copy my marks") or plain chat requests by page or photo number. Apply them in the config,
rebuild, check each change really happened, show it. Details: `references/plan-page.md`. Typical requests:
replace, swap, add back, full page, background photo, straighten (test 3 angles on a grid, pick by eye),
enhance (show before/after), new photos from a new link (fetch into a sub-folder, number them after the last
photo), move or reword a title, cover photo and cover title (`make_cover_photo.py`, `make_cover_title.py`).
No generative edits, ever. Back up plan.json and album_config.py before each round.

## Stage 6 · The album editor
**Lupa:** the user signs in and creates the book (product, size, pages, theme) and uploads one photo. Then follow
"Push procedure" in `references/lupa.md`: build files, upload what is missing (≤10 MB batches), load
`lupa_apply.js`, rebuild only the changed spreads, save, reload, screenshot, check. Use `patch()` for tiny
changes so the user's own edits in the editor stay. Order of scripts every round:
`lupa_layout.py → lupa_titles.py → restamp_tiles.py → make_html.py → check_book.py`.
**Other makers:** print-ready page/spread files and a guided upload (`references/other-companies.md`).

## Stage 7 · QR codes
Offer a QR code per place that has a video album. Ask for each link, make the code, name it from the linked
item's own date and place, and place it on background with the layering rules: `references/qr-rules.md`.
A QR is always the top layer and never crosses a photo's edge.

## Stage 8 · Final check, then the user orders
1. `python3 check_book.py`: sharpness of every photo, cropping, overlaps, duplicates, QR size / trim / top layer /
   straddling. In Lupa also `claudeLupa.check()`.
2. Look at every spread in the editor (go page by page by setting the page index and reloading; screenshot each).
   Look for: hidden or cut text, boxes behind text, misplaced QR codes, empty areas, repeated headers.
3. Spell-check every page title, the cover title and the spine text; keep one spelling of each word.
4. Answer print-quality worries with evidence: the stored file size and dpi, and a 100% crop of the real file.
5. Price table again with the best option and its deadline. Stop at "ready to order".

## Files in this skill
- `scripts/`: the pipeline (fetch, review merge, layout, tuning, map, plan page, Lupa layout and titles, QR,
  restamping, cover, final check) and `lupa_apply.js` (runs inside the Lupa editor tab).
- `references/`: design-rules, lupa, other-companies, plan-page, qr-rules, locations, cowork-setup, review_prompt.
- `assets/`: album_config_template.py, plan.css, plan.js.

## License

Version 2.0 is available for personal and other noncommercial use under the PolyForm Noncommercial License
1.0.0. Commercial use requires a separate written license from Idan Shenhav. See `LICENSE` and
`COMMERCIAL-LICENSE.md`; this includes copying, pitching, selling, licensing, or providing the skill to a print
house, album maker, photo-book company, or other business. The `LICENSE` file governs.
