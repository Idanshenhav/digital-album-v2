# Photo review brief (one subagent per ~140 photos, all launched in one message)

Fill in <TRIP>, <FAMILY>, <RANGE>, <SHEETS>, <PART>. Give each agent example place names from its part of the trip.

"""
You are helping curate a printed family photo album from <TRIP, e.g. "a 2-month family motorhome
trip in the USA, Aug 9 – Oct 8 2021">. Family: <FAMILY, e.g. dad, mom, 3 boys + 1 girl>. Photos are numbered in
camera-time order.

Your chunk: photos <RANGE> (contact sheets <SHEETS>).
Files in <ALBUM FOLDER>:
- sheets/sheet_XXX-YYY.jpg — 20 photos each, number in a yellow box top-left. Read them with the Read tool.
- thumbs/NNN.jpg (600 px) — open single photos for a closer look (duplicates, sharpness, closed eyes, signs).
- items.json — n, local time (timezone may be wrong), orient, w, h, mp, bright/contrast/sat, gap_min.

For EVERY photo record: n; place (specific, consistent spelling, "?" if unsure — photos minutes apart in the
same scenery share a place); scene (max 12 words, who + what); people ("family group" | "some family" |
"one person" | "none"); quality 1-5; verdict "keep"/"out"; reason (required when out, specific, e.g.
"near-duplicate of 57 (57 sharper)"); hero (true only for an outstanding landscape or family photo worth a full
page, ~1 in 25); fix (brighten, darken, more contrast, more saturation, less saturation, warm up, cool down,
straighten horizon, crop tighter, recover sky/highlights, lift shadows, none).

Rules (family album — memories matter as much as quality): keep about 55–65%; from bursts keep the best 1–2 and
name the kept one; out = blurry, badly exposed, accidental, documents/screenshots/receipts, weak repetitive
scenery, mundane. Keep RV/home-on-wheels life moments. Judge duplicates within your chunk only.

Write a JSON array to <ALBUM FOLDER>/notes/part<PART>.json with exactly the keys n, place, scene, people, quality,
verdict, reason, hero, fix — every number once. Validate with python. Change no other files.
Final reply: 5-10 lines — places in order with number ranges, keep/out counts, hero numbers, anything odd
(e.g. a camera whose times look wrong).
"""
