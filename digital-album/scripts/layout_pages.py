"""Add crop-free frame positions (cm) to every page in plan.json.

Dutch book (lay-flat): when both pages of an open spread show the same place, the two
pages are laid out as one 60 x 22 cm canvas and photos may cross the middle.
"""
import json

import layout
from layout import GAP, best_layout

PW, PH = 30.0, 22.0  # Lupa Panoramic Large page, cm
BOX = (1.0, 2.4, 28.0, 18.6)  # photo area under the page title
SPREAD_BOX = (1.0, 2.4, 58.0, 18.6)  # merged spread: left page 0–30 cm, right page 30–60 cm
INTRO_BOX = (1.0, 2.4, 16.8, 18.6)  # right intro page: photos left, text box right
INTRO_SPREAD_BOX = (1.0, 2.4, 46.6, 18.6)  # intro spread: photos across the fold, text box on the right page
SWAPS: list[tuple[int, int]] = []  # photo pairs that trade places (from the review marks)
SAME_SIZE: list[tuple[int, ...]] = []  # photos shown side by side at the same height
LOW_FILL = 0.86
INTRO_TEXT_BOX = True  # False: the motorhome intro spread has no text box (its text lives on the opening-words page)
SPREAD_3_PLACES = False  # True: spreads with 3 places are laid out as one canvas with 3 areas
TEXT_HALF: dict[str, dict] = {}
TEXT_BOX = (1.0, 2.4, 13.6, 18.6)  # text half of a left page (spread coords); photos use the rest of the spread
BIGGER: list[tuple[int, int]] = []  # (a, b): photo a gets a bigger frame than b (layout is recomputed, not refitted)
FILL_PICKS: list[int] = []
LOCK_FILE = ""  # when the book is locked, the fill-up may only re-add FILL_PICKS  # photos the fill-up step added in a version the user already reviewed: keep them when they still fit
import os, sys  # noqa: E401
sys.path.insert(0, os.getcwd())
try:
    from album_config import *  # noqa: F401,F403  (per-album settings; run from the album folder)
except ImportError:
    pass
layout.BIGGER = list(BIGGER)



def fit(aspect: float, W: float, H: float) -> dict[str, float]:
    """Largest uncropped rectangle of this aspect, centered in W x H."""
    w, h = (W, W / aspect) if W / H < aspect else (H * aspect, H)
    return {"x": round((W - w) / 2, 2), "y": round((H - h) / 2, 2), "w": round(w, 2), "h": round(h, 2)}


def lay_pairs(items: list[tuple[int, float]], W: float, H: float, x0: float = 0, y0: float = 0) -> dict:
    """best_layout, but photos listed together in SAME_SIZE are kept side by side at the same height."""
    items = list(items)
    comps: dict[int, list[tuple[int, float]]] = {}
    for k, group in enumerate(SAME_SIZE):
        here = [it for it in items if it[0] in group]
        if len(here) == len(group) > 1:
            cid = -1000 - k
            pos = min(items.index(it) for it in here)
            for it in here:
                items.remove(it)
            items.insert(pos, (cid, sum(a for _, a in here)))
            comps[cid] = here
    out = best_layout(items, W, H, x0, y0)
    rects = []
    for r in out["rects"]:
        if r["n"] in comps:
            parts = comps[r["n"]]
            total = sum(a for _, a in parts)
            x, inner = r["x"], r["w"] - GAP * (len(parts) - 1)
            for n, a in parts:
                w = inner * a / total
                rects.append({"n": n, "x": round(x, 2), "y": r["y"], "w": round(w, 2), "h": r["h"]})
                x += w + GAP
        else:
            rects.append(r)
    out["rects"] = rects
    return out


def spread_layout(groups: list[list[int]], asp: dict[int, float], ph: dict[int, dict],
                  box: tuple = SPREAD_BOX) -> tuple[list, float, list]:
    """Lay out one open spread (60 x 22 cm). One place = one canvas; two or three places = areas, borders may be off the fold."""
    x0, y0, W, H = box
    if len(groups) == 3:
        best = None
        for s1 in range(int(x0 + 12), int(x0 + W - 23), 2):  # s1 < s2: area c (left), b (middle), a (right)
            for s2 in range(s1 + 11, int(x0 + W - 11), 2):
                a, b, c = groups
                la = lay_pairs([(n, asp[n]) for n in reversed(a)], x0 + W - s2 - 0.7, H, s2 + 0.7, y0)
                lb = lay_pairs([(n, asp[n]) for n in reversed(b)], s2 - s1 - 1.4, H, s1 + 0.7, y0)
                lc = lay_pairs([(n, asp[n]) for n in reversed(c)], s1 - 0.7 - x0, H, x0, y0)
                rects = la["rects"] + lb["rects"] + lc["rects"]
                areas = [r["w"] * r["h"] for r in rects]
                sc = sum(areas) / (W * H) * (0.55 + 0.45 * (min(areas) / max(areas)) ** 0.5)
                if best is None or sc > best[0]:
                    best = (sc, rects, sum(areas) / (W * H), s1, s2)
        _, rects, fill, s1, s2 = best
        a, b, c = groups
        titles3 = [{"sec": ph[a[0]]["sec"], "right": x0 + W}, {"sec": ph[b[0]]["sec"], "right": s2 - 0.7},
                   {"sec": ph[c[0]]["sec"], "right": s1 - 0.7}]
        score3 = best[0]
        # a small place can share an area with its neighbour instead: try [a+b | c] and [a | b+c]
        for g2 in ([a + b, c], [a, b + c]):
            r2, f2, t2 = spread_layout(g2, asp, ph, box)
            areas = [r["w"] * r["h"] for r in r2]
            sc2 = f2 * (0.55 + 0.45 * (min(areas) / max(areas)) ** 0.5)
            if sc2 > score3:
                score3, rects, fill = sc2, r2, f2
                both = g2[0] if len(g2[0]) > len(a) or g2[0] is not a else g2[1]
                titles3 = []
                for grp, t in zip(g2, t2):
                    secs = list(dict.fromkeys(ph[n]["sec"] for n in grp))
                    titles3.append({"sec": secs[0], "secs": secs, "right": t["right"]})
        return rects, fill, titles3
    if len(groups) == 1:
        ns = groups[0]
        lay = lay_pairs([(n, asp[n]) for n in reversed(ns)], W, H, x0, y0)  # earliest photo ends on the right (RTL)
        return lay["rects"], lay["fill"], [{"sec": ph[ns[0]]["sec"], "right": x0 + W}]
    a, b = groups
    best = None
    for split in range(int(x0 + 15), int(x0 + W - 13), 2):
        wl, wr = split - 0.7 - x0, x0 + W - split - 0.7
        lr = lay_pairs([(n, asp[n]) for n in reversed(a)], wr, H, split + 0.7, y0)
        ll = lay_pairs([(n, asp[n]) for n in reversed(b)], wl, H, x0, y0)
        areas = [r["w"] * r["h"] for r in lr["rects"] + ll["rects"]]
        sc = sum(areas) / (W * H) * (0.55 + 0.45 * (min(areas) / max(areas)) ** 0.5)
        if best is None or sc > best[0]:
            best = (sc, lr["rects"] + ll["rects"], sum(areas) / (W * H), split)
    _, rects, fill, split = best
    return rects, fill, [{"sec": ph[a[0]]["sec"], "right": x0 + W}, {"sec": ph[b[0]]["sec"], "right": split - 0.7}]


def main() -> None:
    """Compute rects for all pages."""
    plan = json.load(open("plan.json"))
    pages = plan["pages"]
    ph = {p["n"]: p for p in plan["photos"]}
    asp = {n: p["w"] / p["h"] for n, p in ph.items()}
    order = {p["n"]: p["album_order"] for p in plan["photos"]}
    for pg in pages:
        pg.pop("merged", None)
        pg.pop("titles", None)
        pg["shift"] = 0.0
    merged = 0
    filled: list[int] = []
    for k in range(1, len(pages) // 2):
        right, left = pages[2 * k - 1], pages[2 * k]  # page 2k is the right-hand page (read first)
        if right["kind"] == left["kind"] == "intro":
            ns = right["photos"] + left["photos"]
            ib = INTRO_SPREAD_BOX if INTRO_TEXT_BOX else SPREAD_BOX
            lay = lay_pairs([(n, asp[n]) for n in reversed(ns)], ib[2], ib[3], ib[0], ib[1])
            for pg, shift in ((right, PW), (left, 0.0)):
                pg["rects"], pg["fill"], pg["merged"], pg["shift"], pg["titles"] = lay["rects"], lay["fill"], True, shift, [{"sec": right["sec"], "right": 59.0}]
            continue
        if right["kind"] == left["kind"] == "spread" and len(right["photos"]) > 1:  # spread photo + extras on one canvas
            ns = right["photos"]
            x0, y0, W, H = SPREAD_BOX
            main, extras = ns[0], ns[1:]
            mw = min(H * asp[main], W * 0.62)  # the spread photo: full height on the left (may cross the fold)
            mh = mw / asp[main]
            rects = [{"n": main, "x": x0, "y": round(y0 + (H - mh) / 2, 2), "w": round(mw, 2), "h": round(mh, 2)}]
            rest = W - mw - GAP  # extras: smaller, stacked on the right, vertically centered
            lay = lay_pairs([(n, asp[n]) for n in extras], rest, H * 0.75, x0 + mw + GAP, y0 + H * 0.125)
            rects += lay["rects"]
            fill = sum(r["w"] * r["h"] for r in rects) / (W * H)
            titles = [{"sec": right["sec"], "right": x0 + W}]
            for pg, shift in ((right, PW), (left, 0.0)):
                pg.update(kind="photos", rects=rects, fill=round(fill, 3), merged=True, shift=shift, titles=titles)
            merged += 1
            continue
        if right["kind"] == left["kind"] == "photos":  # ("feature" pages are never merged)
            ns = sorted(right["photos"] + left["photos"], key=lambda n: order[n])
            groups: list[list[int]] = []
            for n in ns:
                if groups and ph[groups[-1][0]]["sec"] == ph[n]["sec"]:
                    groups[-1].append(n)
                else:
                    groups.append([n])
            if len(groups) > (3 if SPREAD_3_PLACES else 2):
                continue
            box = SPREAD_BOX
            if left.get("textbox"):  # left half of the left page is kept for text
                tx = TEXT_BOX[0] + TEXT_BOX[2] + 0.8
                box = (tx, SPREAD_BOX[1], SPREAD_BOX[0] + SPREAD_BOX[2] - tx, SPREAD_BOX[3])
            rects, fill, titles = spread_layout(groups, asp, ph, box)
            # wide margins left? try adding a good photo of the same place that was cut for space
            for _ in range(2):
                if fill >= LOW_FILL:
                    break
                ts = [ph[n]["cts"] for g in groups for n in g]
                cands = [p for p in plan["photos"] if p.get("space_cut") and any(p["sec"] == ph[g[0]]["sec"] for g in groups)
                         and (not LOCK_FILE or p["n"] in FILL_PICKS)
                         and min(ts) - 12 * 3600000 <= p["cts"] <= max(ts) + 12 * 3600000]
                best = None
                for c in cands:
                    g2 = [sorted(g + [c["n"]], key=lambda n: order[n]) if ph[g[0]]["sec"] == c["sec"] else g for g in groups]
                    r2, f2, t2 = spread_layout(g2, asp, ph, box)
                    rank = (c["n"] in FILL_PICKS, f2)  # photos already reviewed on this spread win over new picks
                    if f2 >= fill + 0.02 and min(max(r["w"], r["h"]) for r in r2) >= 7 and (best is None or rank > best[5]):
                        best = (g2, f2, r2, t2, c, rank)
                if not best:
                    break
                groups, fill, rects, titles, c, _ = best
                c["keep"], c["space_cut"], c["out_reason"], c["note"] = True, False, "", "Added to fill a wide spread"
                right["photos"] = right["photos"] + [c["n"]]
                filled.append(c["n"])
            for pg, shift in ((right, PW), (left, 0.0)):
                pg["rects"], pg["fill"], pg["merged"], pg["shift"], pg["titles"] = rects, round(fill, 3), True, shift, titles
            merged += 1
    for pg in pages:
        k = pg["kind"]
        if pg.get("merged"):
            continue
        if k in ("hero", "title"):
            n = pg["photos"][0]
            pg["rects"] = [dict(n=n, **fit(asp[n], PW, PH))]
        elif k == "spread":
            n = pg["photos"][0]
            pg["rects"] = [dict(n=n, **fit(asp[n], 2 * PW, PH))]
            pg["shift"] = PW if pg["half"] == "right" else 0.0
        elif pg["photos"]:
            box = TITLE_BOX if k == "title" else INTRO_BOX if (k == "intro" and pg.get("half") == "right") else BOX
            lay = lay_pairs([(n, asp[n]) for n in pg["photos"]], box[2], box[3], box[0], box[1])
            pg["rects"], pg["fill"] = lay["rects"], lay["fill"]
        else:
            pg["rects"] = []
    # Review override: on printed page 57 (plan pages 56–57), keep the Grand Canyon pair
    # together in the upper third of the left-hand page, with #336 on the left and #225 on the right.
    # The shared rect list is intentional: make_html uses the same lay-flat canvas for both halves.
    p56 = next((p for p in pages if p.get("no") == 56), None)
    p57 = next((p for p in pages if p.get("no") == 57), None)
    if p56 and p57 and 336 in p56.get("photos", []) + p57.get("photos", []):
        pair_rects = [
            {"n": 336, "x": 1.0, "y": 2.8, "w": 13.3, "h": 7.48},
            {"n": 225, "x": 15.2, "y": 2.8, "w": 13.8, "h": 7.76},
        ]
        for pg in (p56, p57):
            pg["kind"], pg["merged"], pg["shift"] = "photos", True, (PW if pg is p56 else 0.0)
            pg["rects"], pg["fill"], pg["titles"] = pair_rects, round(sum(r["w"] * r["h"] for r in pair_rects) / (2 * PW * PH), 3), [{"sec": "S22", "right": 59.0}]
        p56["photos"], p57["photos"] = [], [336, 225]

    # Review override for printed page 39: replace the former #225 area with #255 and #212.
    # Keep the rest of the shared S16/S17 spread intact and split that lower-right frame evenly.
    p38 = next((p for p in pages if p.get("no") == 38), None)
    p39 = next((p for p in pages if p.get("no") == 39), None)
    if p38 and p39 and p38.get("merged"):
        base = [r for r in p38.get("rects", []) if r["n"] not in {221, 255, 212}]
        base += [
            {"n": 255, "x": 38.7, "y": 9.13, "w": 9.8, "h": 11.87},
            {"n": 212, "x": 49.2, "y": 9.13, "w": 9.8, "h": 11.87},
        ]
        for pg in (p38, p39):
            pg["rects"] = base
        p38["photos"] = [209, 222, 255, 212]
        p39["photos"] = [238, 239, 240, 228]

    # swaps: exchange two photos' frames (same page, same spread, or different pages); if the shapes differ,
    # each photo is fitted inside the other's frame, so nothing is cropped
    def frame_of(n: int) -> dict | None:
        for pg in pages:
            for r in pg.get("rects", []):
                if r["n"] == n:
                    return r
        return None

    done_swaps: list[tuple[int, int]] = []
    for a, b in SWAPS:
        ra, rb = frame_of(a), frame_of(b)
        if not (ra and rb):
            print(f"swap #{a}/#{b} skipped: one of them is not in the book")
            continue
        # each frame keeps its place and receives the other photo (fitted inside it, so nothing is cropped)
        for r, n in ((ra, b), (rb, a)):
            f = fit(asp[n], r["w"], r["h"])
            if f["w"] >= r["w"] * (1 - layout.MAX_TRIM) and f["h"] >= r["h"] * (1 - layout.MAX_TRIM):
                r.update(n=n)  # within the 5% trim rule: the photo fills its new frame (keeps the gaps even)
            else:
                r.update(n=n, x=round(r["x"] + f["x"], 2), y=round(r["y"] + f["y"], 2), w=f["w"], h=f["h"])
        done_swaps.append((a, b))
    for pg in pages:  # page photo lists follow the frames (merged spreads are handled below)
        if pg.get("rects") and not pg.get("merged"):
            pg["photos"] = sorted({r["n"] for r in pg["rects"]}, key=lambda n: order[n])
    # a photo in a merged spread belongs to the page that holds its center
    for k in range(1, len(pages) // 2):
        right, left = pages[2 * k - 1], pages[2 * k]
        if right.get("merged"):
            rp = [r["n"] for r in right["rects"] if r["x"] + r["w"] / 2 >= PW]
            lp = [r["n"] for r in right["rects"] if r["x"] + r["w"] / 2 < PW]
            right["photos"], left["photos"] = sorted(rp, key=lambda n: order[n]), sorted(lp, key=lambda n: order[n])
    page_of = {}
    for pg in pages:
        for n in pg["photos"]:
            page_of.setdefault(n, pg["no"])
    for p in plan["photos"]:
        p["page"] = page_of.get(p["n"]) if p["keep"] else None
    json.dump(plan, open("plan.json", "w"), ensure_ascii=False, indent=1)
    fills = [pg["fill"] for pg in pages if "fill" in pg]
    small = sorted({(r["n"], r["w"], r["h"]) for pg in pages for r in pg.get("rects", []) if max(r["w"], r["h"]) < 7})
    print("added to fill wide spreads:", filled)
    print("swaps applied:", done_swaps)
    print("merged spreads", merged, "avg fill", round(sum(fills) / len(fills), 2), "small photos", small)


if __name__ == "__main__":
    main()
