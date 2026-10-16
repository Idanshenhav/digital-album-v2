# Lupa (lupa.co.il): products, deals and the editor route

Facts checked October 2026. **Re-check prices, sales and coupon terms live before quoting.**

## Where to look
- Price list with a page-count calculator: https://www.lupa.co.il/tariff/books/
- Dutch book: https://www.lupa.co.il/products/layflat/ · themes: https://www.lupa.co.il/boutiq/
- Shipping: https://www.lupa.co.il/deliveries/ · newsletter coupon: https://www.lupa.co.il/subscription/
- Decline non-essential cookies. Close newsletter pop-ups. Never sign up or log in for the user.

## Products
- Sizes: square small 20×20, square large 30×30, classic plus 22.5×29, **panoramic large 30×22** (landscape), mini 15×15.
- Covers: soft, hard, or **Dutch book (הספר ההולנדי)**: thick premium pages that open 180° flat (lay-flat). It is
  Lupa's top paper; there is no separate paper menu. Full-bleed single photos on a spread need the Dutch book.
- Pages: hard cover up to 144. **Dutch book up to 100.** Web/app adds pages 2 at a time, the desktop software 4.
  The editor shows 101 pages for a 100-page book (the opening-words page is free).
- Example prices (Oct 2026): Dutch, panoramic 30×22, 100 pp = 514 ₪ list. Hard cover panoramic 100 pp = 327 ₪.

## Deals: how to compare
- Lupa runs site-wide sales (e.g. 30% off, automatic, with an end date). Terms say **no stacking**: sales, coupons
  and vouchers do not combine.
- Vouchers from clubs and benefit portals (e.g. "pay 160, get 300") usually count against the **list** price. Show
  every option: sale price; voucher on list price (voucher cost + list − voucher value); two vouchers if allowed.
  Tell the user which voucher terms to check (works during a sale? more than one per order? covers shipping? expiry?).
- Shipping: free locker pickup in some cities, pickup point, home courier. Show the total with shipping.
- Never add to cart or order. The user orders.

## Themes
Pick 3–5 that fit the trip (nature, cities, beach, kids). Save sample images to `themes/` and show them. The theme
gives page backgrounds and colours. Our titles and QR codes adapt their colours to it.

## The editor route ("hybrid": our layout on Lupa's theme)
The web editor (online-v3.lupa.co.il/preview/<token>) keeps the book as a JSON tree. `scripts/lupa_apply.js`
rewrites that tree from `ready/lupa_layout.json` and saves it with the same call the editor makes.

### One-time setup (the user does the clicks that need them)
1. The user signs in and creates the book: product, size, page count, theme. They upload at least one photo so the
   editor builds a book.
2. Claude reads the theme: `claudeLupa.themeInfo()` → save the result as `ready/lupa_theme.json`.

### Push procedure (every round)
1. Build files: `lupa_layout.py → lupa_titles.py → restamp_tiles.py → make_html.py`, then `check_book.py`.
2. Find what is missing in Lupa: run `claudeLupa.build({only:[...]})` once; its `miss` list names the files not yet
   uploaded. Upload them: storage panel "אחסון זמני" → "להוספת תמונות" → file input (find it with the page tools)
   → file_upload, **under 10 MB per batch** → "להעלות N קבצים".
3. Load the helper: add a hidden file input (aria-label "claude code loader"), feed it `lupa_apply.js` and
   `ready/lupa_layout.json`, then run `(0,eval)(window.__code)`. Never inject a `<script>` from localhost (it hangs).
4. Start `claudeLupa.build({only:[spreads]})` without waiting (`.then(r => window.__br = r)`), then poll
   `window.__br`. Only the named spreads are rebuilt; every other page keeps the user's own edits.
5. `await claudeLupa.save()`. Then go to a page: set `photo-album-storage` → `state.currentPageIndex = i` in
   localStorage and reload (the next-page arrow is unreliable). Screenshot and check.
6. Tiny changes (move a QR, swap one re-made title, fix the spine text) don't need a rebuild:
   `claudeLupa.patch({moves:[[spread, time, dx, dy]], swaps:[[oldTime, newTime, ratio]], coverText:[from, to]})`
   then `save()`. This keeps the user's manual edits.
7. Cover: upload the cover file, then `claudeLupa.cover({time, ratio, imageFolder, dropTitles: []})` and `save()`.
   The front-cover image folder is the one at X ≈ 1860 on the cover sheet. The spine text is in the cover's
   `m_tree_texts`: fix spelling there too.
8. Final QA in the editor: `claudeLupa.check()`.

### Things that bite (all happened)
- **Matching by EXIF time + shape.** Lupa renames uploads, so every file needs its own EXIF time. A re-made file
  with the same time is silently ignored, and the old picture stays. `restamp_tiles.py` fixes this automatically.
- **800 px minimum**: Lupa refuses smaller images, so title tiles are stored 6–8× larger.
- **One editor tab only.** A second tab or another agent saving an older copy undoes changes.
- **Never click in the "עיצוב הספר" (book design) panel**: one click re-themes the whole book.
- Re-applying a theme resets every frame line to dark grey. lupa_apply sets frame lines explicitly.
- localStorage fills up with backups and the editor jumps to /home: delete old `__claude_backup_tree_*` keys
  (keep `_orig`).
- `save()` waits for the editor's auth header; it falls back to the token in `user-storage`. Never print it.
- Long JS calls time out (~45 s): run builds async and poll. Long outputs get cut: return short JSON.
- The editor's preview of a full page is 1282 px wide and looks soft. Lupa stores full pages at ~277 dpi (spreads
  6547×2400). Check stored sizes with `check()` (`minDpi`), not the screen.
- The editor may show a stale page after saving: reload once more before judging.
- The inside back cover is not printable (the last spread has only page 100).
- Lupa's own text tools (page title, cover title) ignore bold, colour and "no box". That is why titles and the
  cover title are drawn into images.
- A tab in the background can't be screenshotted: check the saved data instead, or ask the user to bring it front.
