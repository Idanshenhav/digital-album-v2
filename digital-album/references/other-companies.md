# Any other album maker: research, then print files and a guided upload

For makers other than Lupa, Claude does the research, the plan and print-ready files, then guides the upload step
by step while watching the screen. It does not rewrite the maker's editor data (that is only built for Lupa).

## 1. Research checklist (live, with sources)
Use web search and the browser. Decline non-essential cookies; never sign up, log in or add to cart.
- **Products:** sizes (cm), orientation, cover types, paper, lay-flat option, min/max pages and the page step
  (2 or 4), price per extra page.
- **Editor:** web, app or desktop software? Can you upload whole pages/spreads as single images (full bleed)?
  Can frames be resized freely? Text limits? Does it take QR codes?
- **Print specs:** page size in px at 300 dpi, bleed (mm), safe area, colour space, file type and size limits.
- **Deals:** current sale (%, end date, automatic or code), newsletter coupon, club / credit-card / workplace
  vouchers (e.g. "pay 160, get 300"), whether deals stack (usually not), shipping and pickup costs.
- Report a table: option, discount, conditions, valid until, source URL, and the final price for the user's page
  count with shipping. Recommend one and say why.

## 2. Make the files
1. Build the plan as usual (all stages up to the HTML plan and review rounds).
2. Set the page size from the maker's spec (width × height cm at 300 dpi, plus bleed on every outer edge).
3. Render every open spread as one image (lay-flat books) or every page alone, in page order, with titles and QR
   codes drawn in: `render_spreads.py` (pre-composed full pages with the blurred fill, titles with no box).
4. Name files `001.jpg, 002.jpg…` so the editor keeps the order. Export the cover separately with its title.
5. Run `check_book.py`-style checks by eye: nothing important within the safe margin, QR at least 2 cm, no QR
   crossing a photo's edge.

## 3. Guided upload
- The user signs in and creates the book (size, cover, page count, theme "none" or plain white).
- Claude gives one short step at a time and watches with screenshots: upload the files, set each page to a
  full-bleed single-photo layout, check page order, set the cover. Fix anything that drifted.
- Last: a full visual pass of every page in the editor preview, then the price table again. The user orders.
