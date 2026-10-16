# The HTML plan page

`make_html.py` writes one self-contained page (`OUTPUT_HTML`): photos are embedded, so it opens anywhere. Serve it
on localhost and show it in the browser pane (file:// pages can't be opened by the browser tools).

## What it shows
- Title line, counts (candidates / kept / out / cut for space / pages, full pages, spreads).
- Trip facts from the family's documents (TRIP_FACTS), the cover and back cover.
- Recommended product and price table (PRODUCT_HTML), the layout rules, reasons for left-out photos.
- The route map, theme recommendations with sample images.
- **Every page** in book order, as open spreads (right page first), drawn to scale: photos with their numbers,
  page titles, QR codes, blurred fills of full pages, text pages. Editor page numbers under each page.
- Photo index of all candidates (in / out with reasons), and new photos added later.

## What the user can do on it (plan.js)
- Click a photo: details (place, time, camera, size in cm, tuning, before/after).
- **Replace**: the red ✕ on a photo, then pick the replacement.
- **Swap** two photos on the same page or spread ("Swap with").
- **Add back** a left-out photo. **Notes** on any photo.
- Marks are saved in the browser (localStorage key STORE_KEY). **Copy my marks** gives a text list to paste in chat.

## Applying a round
1. Ask for the pasted "Copy my marks" text (in Cowork this is the only way; on a Mac,
   `read_chrome_marks.py <STORE_KEY>` can read them from Chrome).
2. Put them in album_config.py: REPLACE, FORCE_OUT, FORCE_KEEP, FORCE_HERO, SWAPS, NOTES. Bump STORE_KEY.
3. A swap marked again means "put them back": remove the old swap, don't add a new one.
4. Rebuild (`build_plan.py → layout_pages.py → make_html.py`), then check that each mark really happened
   (positions before vs after) before saying so. Back up plan.json and album_config.py first.
5. When the user approves the book, set LOCK_FILE so later rounds change only what they ask.

## Chat requests (no marks needed)
The user may just say "page 42: swap 165 and 172", "straighten 328", "make 498 a full page like 496", "use this
photo as the background of pages 49–50", "move the title to page 75", "enhance 433", "add this new photo
(link)". Translate editor page numbers to plan page numbers (plan = editor − 1 for Lupa), change the config,
rebuild, show the result in the plan, then push to the editor if the user is in that stage.
