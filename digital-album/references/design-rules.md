# Design rules (proven on a 100-page printed book)

These rules came from many review rounds on a real album that printed perfectly. Follow them unless the user
asks for something else, and tell the user when a request breaks one (then do what they ask).

## Book
- Read right to left (Hebrew books). An open spread = the right page first. Page titles may be Hebrew or English.
- Page numbers: use the album editor's numbers when talking to the user (Lupa counts its opening-words page as
  page 1, so editor page = plan page + 1).
- Lay-flat books (Lupa "Dutch book") open 180° flat: one place across both pages = one 60×22 cm canvas, and photos
  may cross the fold.

## Order
- Strict camera-time order, after fixing wrong camera clocks (one camera is often hours off; duplicate shots from
  two cameras give the exact offset). Then group by place: same place = same page(s). Drone shots and a second
  camera join their place.
- Story beats camera time only on purpose (e.g. a "life in the motorhome" intro spread, a key moment moved one page).
  Use ORDER_BEFORE in the config. Never change a photo's time.

## Layout
- **Never crop.** Each frame keeps the photo's own shape. Portrait stays portrait, 16:9 stays 16:9. Only exception:
  up to 5% off one side to close a wide gap.
- A full-page or double-page photo every 5–7 pages (big landscapes, strong family photos). It keeps its shape, and a
  blurred copy of the same photo fills the rest of the page **and continues across the facing page**.
- Every photo gets a number and a visible preview. Every left-out photo gets a reason. Show counts: candidates /
  kept / out / cut for space.
- A page can be left partly empty on purpose for handwriting. Ask before filling space the user left.

## Text
- Page title ≤ 45 characters, photo caption ≤ 21 (Lupa limits; check other makers).
- **No box or background behind any text.** Text colour stands out from the page: white on dark, near-black on light.
- **Never repeat a page header.** A header appears on the first page of its place only.
- No icons, symbols or flags in headers.
- Distances: kilometres first, miles in brackets (e.g. "9,100 km (5,666 mi)").
- Notes to the user inside the plan are in the user's chat language; book text in the album's language.
- Spell-check every title before printing. Keep one spelling of a word across the whole book, the cover and the spine.

## Map
- From the photos' own locations, on real roads (OSRM). Each US state in its own colour with borders and names
  (other countries: route and stops only). Stats line: distance, and number of states for US trips.
- Credit Esri and OpenStreetMap/OSRM. No state flags or park logos.

## Photo quality
- Print tuning per photo: brightness, contrast, saturation; lift shadows on faces in shade; straighten tilted
  horizons (find the angle by testing 3 angles against a grid, pick by eye; a sea horizon or railing is the guide).
- Full-size originals only (Google Photos `<url>=d`). JPEG q95, sRGB. Never upscale or over-sharpen; flag photos
  that are too small for their frame instead.
- **No generative edits, ever**: no AI fill, no removing objects, no changing faces or people. Only normal photo
  controls. For RAW files, use the user's darktable (or similar) exports; export full size, quality 100.
- Before replacing a photo with a tuned version, show before/after side by side and wait for a yes.
- The editor's on-screen preview of a full page is small (Lupa: 1282 px across a whole spread) and looks soft.
  That is not the print. Check the real file at 100% and the stored size (Lupa keeps ~277 dpi for full pages).
