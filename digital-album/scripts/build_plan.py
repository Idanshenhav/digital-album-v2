"""Build the Lupa album plan (data + layout) for one trip album.

Reads items.json (photo metadata) and notes/part*.json (per-photo review),
writes plan.json with sections, pages and per-photo decisions.
"""
import json
import math
from typing import Any

HOUR = 3600000
BOOK_MAX_PAGES = 100  # the product's page limit (Lupa Dutch book: 100)
BOOK_MIN_PAGES = 24  # the product's minimum
BOOK_PAGE_STEP = 4  # pages are added in steps of this (Lupa desktop software: 4)
BOOK_PAGES = None  # a fixed page count; None = the natural length, rounded up to the step

# ---- defaults; every album overrides these in album_config.py (run the scripts from the album folder) ----
SECTIONS: list[tuple[str, str, str, list[str]]] = []  # (id, Hebrew title, English name, keywords in the review "place")
FORCE_SECTION: dict[int, str] = {}
INTRO_PHOTOS: list[int] = []
INTRO_BRING_BACK: dict[int, str] = {}
COVER: int | None = None
DEPARTURE: list[int] = []
REPLACE: dict[int, int] = {}
FORCE_OUT: dict[int, str] = {}
FORCE_KEEP: set[int] = set()
FORCE_HERO: set[int] = set()
NOTES: dict[int, str] = {}
SPREAD_FORCE: set[int] = set()
INTRO_AFTER = ""
CLOCK_FIXES: list[dict[str, float]] = []
COVER_ONLY = False  # True: the COVER photo is on the book cover only; page 1 = map, page 2 = opening words, page 3 = departure
NO_HERO: set[int] = set()
OPENING_AFTER_DEPARTURE = False
OPENING_PHOTO: int | None = None  # COVER_ONLY: page 2 = this photo, big, inside the theme margins (opening words sit facing page 1)  # never promote these to a full page
TEXT_HALF: dict[str, dict] = {}
SPREAD_EXTRA: dict[int, list[int]] = {}  # {spread photo: [extra photos]}: that double page shows these photos too  # {section: {"photos": [...], ...}}: that section's filler page gets these photos + a text half
PAGE_MAX: dict[str, int] = {}  # {section: n}: allow up to n photos on one page there (keeps the page count stable)
ORDER_BEFORE: dict[int, int] = {}
FILL_PICKS: list[int] = []
LOCK_FILE = ""  # e.g. "plan_locked.json": keep the reviewed photo set and full pages; only marks change them  # {a: b}: photo a goes right before photo b in the book (story order beats camera time)
SPREAD_ASPECT = 2.4  # wider than this -> double-page spread

import os, sys  # noqa: E401
sys.path.insert(0, os.getcwd())
try:
    from album_config import *  # noqa: F401,F403
except ImportError:
    sys.exit("album_config.py not found — run from the album folder")
SEC = {s[0]: {"id": s[0], "he": s[1], "en": s[2]} for s in SECTIONS}
FIRST_SEC, LAST_SEC = SECTIONS[0][0], SECTIONS[-1][0]



def target_pages(natural: int) -> int:
    """Book length: BOOK_PAGES if set, else the natural length rounded up to the page step, within min..max."""
    if BOOK_PAGES:
        return BOOK_PAGES
    return min(BOOK_MAX_PAGES, max(BOOK_MIN_PAGES, math.ceil(natural / BOOK_PAGE_STEP) * BOOK_PAGE_STEP))

def load() -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]]]:
    """Load photo metadata and review notes."""
    rows = json.load(open("items.json"))
    notes: dict[int, dict[str, Any]] = {}
    import glob
    for f in sorted(glob.glob("notes/part*.json")):
        for x in json.load(open(f)):
            notes[x["n"]] = x
    return rows, notes


def corrected_ts(r: dict[str, Any]) -> int:
    """Camera time, with known wrong camera clocks fixed (CLOCK_FIXES in album_config.py)."""
    for fx in CLOCK_FIXES:
        if r["mp"] == fx["mp"] and ("tz_hours" not in fx or (r["tz"] or 0) == fx["tz_hours"] * HOUR):
            return r["ts"] + int(fx["shift_hours"] * HOUR)
    return r["ts"]


def section_of(place: str) -> str | None:
    """Map a review place name to a trip section by keywords."""
    p = place.lower()
    hits = [(len(k), sid) for sid, _, _, kws in SECTIONS for k in kws if k in p]
    return max(hits)[1] if hits else None


def assign_sections(rows: list[dict[str, Any]], notes: dict[int, dict[str, Any]]) -> None:
    """Assign every photo to a section; photos with a generic place go to the nearest-in-time labeled neighbour."""
    for r in rows:
        r["sec"] = FORCE_SECTION.get(r["n"]) or section_of(notes[r["n"]]["place"])
    for i, r in enumerate(rows):
        if r["sec"]:
            continue
        best, gap = None, None
        for j in range(len(rows)):
            if rows[j]["sec"] and rows[j]["n"] not in FORCE_SECTION and section_of(notes[rows[j]["n"]]["place"]):
                g = abs(rows[j]["cts"] - r["cts"])
                if gap is None or g < gap:
                    best, gap = rows[j]["sec"], g
        r["sec"] = best


def order_by_scenery(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep camera-time order but pull stray photos (drone, second camera) into their place group."""
    visits: list[list[dict[str, Any]]] = []
    for r in rows:
        if visits and visits[-1][0]["sec"] == r["sec"]:
            visits[-1].append(r)
        else:
            visits.append([r])
    changed = True
    while changed:
        changed = False
        for i, v in enumerate(visits):
            if len(v) > 3:
                continue
            for j in range(len(visits)):
                if j != i and visits[j][0]["sec"] == v[0]["sec"] and len(visits[j]) > len(v) \
                        and abs(visits[j][0]["cts"] - v[0]["cts"]) < 36 * HOUR and abs(i - j) <= 4:
                    visits[j] = sorted(visits[j] + v, key=lambda x: x["cts"])
                    visits.pop(i)
                    changed = True
                    break
            if changed:
                break
        merged: list[list[dict[str, Any]]] = []
        for v in visits:
            if merged and merged[-1][0]["sec"] == v[0]["sec"]:
                merged[-1] = sorted(merged[-1] + v, key=lambda x: x["cts"])
            else:
                merged.append(v)
        visits = merged
    return [r for v in visits for r in v]


def tuning(r: dict[str, Any], fix: str) -> dict[str, int]:
    """Suggested print tuning in percent: brightness, contrast, saturation (prints look flatter than screens)."""
    b = (122 - r["bright"]) / 255 * 90
    c = (58 - r["contrast"]) * 0.6 + 5
    s = (100 - r["sat"]) * 0.25 + 8
    f = fix.lower()
    if "brighten" in f or "lift shadows" in f:
        b += 8
    if "darken" in f or "recover" in f:
        b -= 8
    if "more contrast" in f:
        c += 8
    if "more saturation" in f:
        s += 8
    if "less saturation" in f:
        s -= 12
    clamp = lambda v, lo, hi: int(round(max(lo, min(hi, v))))
    return {"bright": clamp(b, -20, 30), "contrast": clamp(c, 0, 25), "sat": clamp(s, -10, 30)}


def page_split(items: list[dict[str, Any]], per_max: int | None = None) -> list[list[dict[str, Any]]]:
    """Split a section's regular photos into pages of 2–4 (5 if mostly portraits), evenly."""
    n = len(items)
    if n == 0:
        return []
    per = 5
    if sum(1 for x in items if x["orient"] == "P") > n / 2:
        per = 6
    per = per_max or per
    pages = max(1, math.ceil(n / per))
    size = [n // pages + (1 if k < n % pages else 0) for k in range(pages)]
    out, i = [], 0
    for s in size:
        out.append(items[i:i + s])
        i += s
    return out


def build() -> dict[str, Any]:
    """Build the whole plan."""
    rows, notes = load()
    for r in rows:
        r["cts"] = corrected_ts(r)
        nt = notes[r["n"]]
        r.update({k: nt[k] for k in ["place", "scene", "people", "quality", "reason", "fix"]})
        r["keep"] = nt["verdict"] == "keep"
        r["hero"] = bool(nt["hero"]) and r["keep"]
        r["aspect"] = max(r["w"], r["h"]) / min(r["w"], r["h"])
        r["tune"] = tuning(r, nt["fix"])
        r["out_reason"] = "" if r["keep"] else nt["reason"]
    for n, why in INTRO_BRING_BACK.items():
        r = next(x for x in rows if x["n"] == n)
        r["keep"], r["out_reason"], r["note"] = True, "", why
    by_n0 = {x["n"]: x for x in rows}
    for a, b in REPLACE.items():
        by_n0[a]["keep"], by_n0[a]["out_reason"] = False, f"Replaced by #{b} (your choice)"
        by_n0[b]["keep"], by_n0[b]["out_reason"], by_n0[b]["note"] = True, "", f"Replaces #{a} (your choice)"
    for n, why in FORCE_OUT.items():
        by_n0[n]["keep"], by_n0[n]["out_reason"] = False, why
    for n in FORCE_KEEP:
        by_n0[n]["keep"], by_n0[n]["out_reason"] = True, ""
    for n, why in NOTES.items():
        by_n0[n]["note"] = why
    for a, b in ORDER_BEFORE.items():
        by_n0[a]["cts"] = by_n0[b]["cts"] - 1000
    rows.sort(key=lambda r: r["cts"])
    assign_sections(rows, notes)
    rows = order_by_scenery(rows)
    for i, r in enumerate(rows):
        r["album_order"] = i + 1

    def npages(pages: list[dict[str, Any]]) -> int:
        """Pages used so far (a spread photo takes 2)."""
        return sum(2 if p["kind"] == "spread" else 1 for p in pages)

    def by_keep(n: int) -> bool:
        return any(r["n"] == n and r["keep"] for r in rows)

    def layout(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if COVER_ONLY:
            pages: list[dict[str, Any]] = [
                {"kind": "map", "photos": [], "sec": FIRST_SEC, "note": "Route map (map/route_map.png)"},
                ({"kind": "feature", "photos": [OPENING_PHOTO], "sec": FIRST_SEC, "note": "One big photo, room for text around it"}
                 if OPENING_PHOTO else {"kind": "opening", "photos": [], "sec": FIRST_SEC, "note": "Opening words (Lupa text page – editable)"}),
                {"kind": "photos", "photos": DEPARTURE, "sec": FIRST_SEC, "note": "Goodbye to the dog, airport, plane"}]
            if OPENING_AFTER_DEPARTURE:  # leaving home first, then the big motorhome photo
                pages[1], pages[2] = pages[2], pages[1]
        else:
            pages = [
                {"kind": "title", "photos": [COVER] if COVER else [], "sec": FIRST_SEC, "note": "Opening page – one family photo in big scenery"},
                {"kind": "photos", "photos": DEPARTURE, "sec": FIRST_SEC, "note": "Goodbye to the dog, airport, plane"},
                {"kind": "map", "photos": [], "sec": FIRST_SEC, "note": "Route map (map/route_map.png)"}]
        seq: list[list[dict[str, Any]]] = []
        for r in rows:
            if r["n"] in INTRO_PHOTOS or not r["keep"] or r["n"] in DEPARTURE or r["n"] == COVER or r["n"] == OPENING_PHOTO \
                    or any(r["n"] in t["photos"] for t in TEXT_HALF.values()) \
                    or any(r["n"] in v for v in SPREAD_EXTRA.values()):
                continue
            if seq and seq[-1][0]["sec"] == r["sec"]:
                seq[-1].append(r)
            else:
                seq.append([r])
        intro_done = False
        pending_small: list[dict[str, Any]] = []
        for grp in seq:
            sid = grp[0]["sec"]
            if INTRO_PHOTOS and not intro_done and sid > INTRO_AFTER:
                pages.append({"kind": "intro", "photos": INTRO_PHOTOS[:4], "sec": INTRO_AFTER, "half": "right"})
                pages.append({"kind": "intro", "photos": INTRO_PHOTOS[4:], "sec": INTRO_AFTER, "half": "left"})
                intro_done = True
            heroes = [x for x in grp if x["hero"]]
            regular = [x for x in grp if not x["hero"]]
            chunks = page_split(regular, PAGE_MAX.get(sid))
            # tiny sections (1–2 photos, no hero) share a page with the next tiny section
            if not heroes and len(regular) <= 2:
                pending_small.extend(regular)
                if len(pending_small) >= 3:
                    pages.append({"kind": "photos", "photos": [x["n"] for x in pending_small],
                                  "sec": pending_small[0]["sec"], "secs": sorted({x["sec"] for x in pending_small})})
                    pending_small = []
                continue
            if pending_small:
                if chunks and len(chunks[0]) + len(pending_small) <= 6:
                    chunks[0] = pending_small + chunks[0]
                else:
                    pages.append({"kind": "photos", "photos": [x["n"] for x in pending_small], "sec": pending_small[0]["sec"]})
                pending_small = []
            # place heroes in time order between the regular pages
            items: list[tuple[int, Any]] = [(c[0]["cts"], ("reg", c)) for c in chunks]
            items += [(h["cts"], ("hero", h)) for h in heroes]
            for _, (kind, obj) in sorted(items, key=lambda t: t[0]):
                if kind == "reg":
                    pages.append({"kind": "photos", "photos": [x["n"] for x in obj], "sec": sid})
                elif obj["aspect"] >= SPREAD_ASPECT or obj["n"] in SPREAD_FORCE:
                    pages.append({"kind": "spread", "photos": [obj["n"]] + [n for n in SPREAD_EXTRA.get(obj["n"], []) if by_keep(n)], "sec": sid})
                else:
                    pages.append({"kind": "hero", "photos": [obj["n"]], "sec": sid})
            if INTRO_PHOTOS and sid == INTRO_AFTER and not intro_done:
                pages.append({"kind": "intro", "photos": INTRO_PHOTOS[:4], "sec": INTRO_AFTER, "half": "right"})
                pages.append({"kind": "intro", "photos": INTRO_PHOTOS[4:], "sec": INTRO_AFTER, "half": "left"})
                intro_done = True
        if pending_small:
            pages.append({"kind": "photos", "photos": [x["n"] for x in pending_small], "sec": pending_small[0]["sec"]})
        # expand spreads to 2 pages, and make sure every spread / intro starts on a right-hand page (even number)
        out: list[dict[str, Any]] = []
        for pg in pages:
            if pg["kind"] in ("spread", "intro") and not (pg["kind"] == "intro" and pg.get("half") == "left"):
                if (len(out) + 1) % 2 == 1:  # next page would be a left page -> swap in the previous regular page
                    prev = out[-1] if out and out[-1]["kind"] == "photos" else None
                    if prev and len(prev["photos"]) >= 4:
                        half = len(prev["photos"]) // 2
                        out[-1] = dict(prev, photos=prev["photos"][:half])
                        out.append(dict(prev, photos=prev["photos"][half:]))
                    elif out and out[-1]["sec"] in TEXT_HALF:  # filler page -> a few photos of the place + a text half
                        out.append({"kind": "photos", "photos": list(TEXT_HALF[out[-1]["sec"]]["photos"]), "sec": out[-1]["sec"],
                                    "textbox": True, "note": "Photos + a text half (your request)"})
                    else:
                        out.append({"kind": "text", "photos": [], "sec": pg["sec"], "note": "Map / text page"})
            if pg["kind"] == "spread":
                out.append(dict(pg, half="right"))
                out.append(dict(pg, half="left"))
            else:
                out.append(pg)
        out.append({"kind": "closing", "photos": [], "sec": LAST_SEC, "note": "Closing page – text & QR to trip videos"})
        if len(out) % 2:
            out.insert(-1, {"kind": "text", "photos": [], "sec": LAST_SEC, "note": "Short text page"})
        return out

    # Heroes: start from the drone/panorama "must" spreads, then add one only where 6 pages pass without one.
    by_n = {r["n"]: r for r in rows}
    agent_hero = {r["n"] for r in rows if r["hero"] and r["n"] not in NO_HERO}
    for r in rows:
        r["hero"] = (r["n"] in SPREAD_FORCE or r["n"] in FORCE_HERO) and r["keep"]

    def score(r: dict[str, Any]) -> tuple:
        return (r["n"] in agent_hero, r["quality"], r["people"] == "family group", r["orient"] == "L", r["mp"])

    def pick_heroes() -> list[dict[str, Any]]:
        for _ in range(60):
            pages = layout(rows)
            last, need = 0, None
            for i, pg in enumerate(pages):
                if pg["kind"] in ("hero", "spread", "intro", "title", "map", "opening"):
                    last = i
                elif i - last >= 7:
                    need = (last, i)
                    break
            if not need:
                return pages
            lo, hi = need
            win = [n for pg in pages[lo + 1:hi + 1] if pg["kind"] == "photos" for n in pg["photos"]]
            late = [n for pg in pages[lo + 4:hi + 1] if pg["kind"] == "photos" for n in pg["photos"]]
            win = [n for n in win if n not in NO_HERO] or win
            late = [n for n in late if n not in NO_HERO]
            pool = [by_n[n] for n in (late or win) if by_n[n]["orient"] == "L" and by_n[n]["quality"] >= 4] or \
                   [by_n[n] for n in win if by_n[n]["orient"] == "L"] or [by_n[n] for n in win]
            best = max(pool, key=score)
            best["hero"] = True
            best["promoted"] = best["n"] not in agent_hero
        return layout(rows)

    lock = json.load(open(LOCK_FILE)) if LOCK_FILE and os.path.exists(LOCK_FILE) else None
    if lock:  # the reviewed book is frozen: only the user's marks change which photos are in and which are full pages
        lk = {q["n"]: q for q in lock["photos"]}
        marked = set(REPLACE) | set(REPLACE.values()) | set(FORCE_KEEP) | set(FORCE_OUT) | set(FORCE_HERO) | set(NO_HERO)
        for r in rows:
            q = lk.get(r["n"])
            if q is None or r["n"] in marked:
                continue
            r["keep"], r["space_cut"] = q["keep"], q.get("space_cut", False)
            r["out_reason"] = "" if q["keep"] else (q.get("out_reason") or r["out_reason"])
            if r["n"] in FILL_PICKS:  # added later by layout_pages' fill-up; let it place them again the same way
                r["keep"], r["space_cut"] = False, True
        for r in rows:
            was = bool(lk.get(r["n"], {}).get("hero"))
            r["hero"] = r["keep"] and ((was and r["n"] not in NO_HERO) or r["n"] in FORCE_HERO or r["n"] in SPREAD_FORCE)
        pages = layout(rows)
        removed = restored = 0
        if len(pages) > BOOK_MAX_PAGES:
            print(f"WARNING: locked book has {len(pages)} pages (> {BOOK_MAX_PAGES}) – raise PAGE_MAX for the section that grew")
        while len(pages) < target_pages(len(pages)):
            pages.insert(-1, {"kind": "text", "photos": [], "sec": LAST_SEC, "note": "Short text page"})
        print("locked to", LOCK_FILE)
    else:
        removed = 0
        pages = pick_heroes()
        while len(pages) > BOOK_MAX_PAGES:
            counts: dict[str, int] = {}
            for r in rows:
                if r["keep"]:
                    counts[r["sec"]] = counts.get(r["sec"], 0) + 1
            pool = [r for r in rows if r["keep"] and not r["hero"] and r["n"] not in INTRO_PHOTOS and r["n"] not in DEPARTURE and r["n"] != COVER and r["n"] not in FORCE_KEEP
                    and counts[r["sec"]] > 3]
            for _ in range(3):
                victim = min(pool, key=lambda r: (r["quality"], r["people"] != "none", -counts[r["sec"]], r["sharp"]))
                victim["keep"] = False
                victim["space_cut"] = True
                victim["out_reason"] = "Cut to fit the page limit – weaker than similar photos of this place (easy to add back)"
                pool.remove(victim)
                counts[victim["sec"]] -= 1
                removed += 1
            for r in rows:
                r["hero"] = (r["n"] in SPREAD_FORCE or r["n"] in FORCE_HERO) and r["keep"]
                r.pop("promoted", None)
            pages = pick_heroes()

        # Lupa desktop software adds pages in steps of 4: fill up to BOOK_MAX_PAGES by bringing back the best cut photos
        restored = 0
        for r in sorted([r for r in rows if r.get("space_cut")], key=lambda r: (-r["quality"], r["people"] == "none")):
            if len(pages) >= target_pages(len(pages)):
                break
            r["keep"], r["space_cut"], r["out_reason"] = True, False, ""
            trial = layout(rows)
            if len(trial) > target_pages(len(pages)):
                r["keep"], r["space_cut"] = False, True
                r["out_reason"] = "Cut to fit the page limit – weaker than similar photos of this place (easy to add back)"
            else:
                pages = trial
                removed -= 1
                restored += 1
        pages2 = pick_heroes()
        while len(pages2) > BOOK_MAX_PAGES:  # new hero pages pushed us over: drop the weakest kept photo
            pool = [r for r in rows if r["keep"] and not r["hero"] and r["n"] not in INTRO_PHOTOS and r["n"] not in DEPARTURE and r["n"] != COVER and r["n"] not in FORCE_KEEP]
            v = min(pool, key=lambda r: (r["quality"], r["people"] != "none", r["sharp"]))
            v["keep"], v["space_cut"] = False, True
            v["out_reason"] = "Cut to fit the page limit – weaker than similar photos of this place (easy to add back)"
            removed += 1
            pages2 = layout(rows)
        pages = pages2
        while len(pages) < target_pages(len(pages)):
            pages.insert(-1, {"kind": "text", "photos": [], "sec": LAST_SEC, "note": "Short text page"})
        print("restored", restored)

    page_of: dict[int, int] = {}
    for i, pg in enumerate(pages):
        pg["no"] = i + 1
        secs = []
        for n in pg["photos"]:
            s = by_n[n]["sec"] if pg["kind"] not in ("intro", "title") else pg["sec"]
            if s not in secs:
                secs.append(s)
        pg["secs"] = secs or [pg["sec"]]
        for n in pg["photos"]:
            page_of.setdefault(n, i + 1)
    for r in rows:
        r["page"] = page_of.get(r["n"])
        if COVER_ONLY and r["n"] == COVER:
            r["page"] = 0  # the book cover
        if r["keep"] and r["page"] is None:
            raise SystemExit(f"kept photo {r['n']} has no page")
    return {"sections": SEC, "pages": pages, "photos": rows, "space_cut": removed}



if __name__ == "__main__":
    plan = build()
    json.dump(plan, open("plan.json", "w"), ensure_ascii=False, indent=1)
    ph, pg = plan["photos"], plan["pages"]
    keep = [p for p in ph if p["keep"]]
    print("pages", len(pg), "keep", len(keep), "out", len(ph) - len(keep), "space cut", plan["space_cut"])
    kinds: dict[str, int] = {}
    for p in pg:
        kinds[p["kind"]] = kinds.get(p["kind"], 0) + 1
    print(kinds)
    last = 0
    gaps = []
    for p in pg:
        if p["kind"] in ("hero", "spread", "intro", "title"):
            gaps.append(p["no"] - last)
            last = p["no"]
    print("hero gaps", gaps)
    print("promoted", [p["n"] for p in ph if p.get("promoted")])
