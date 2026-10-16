"""Turn the album plan into frame positions for Lupa's online editor (hybrid route: our layout, Lupa's theme).

Usage (album folder, after layout_pages.py and make_upload_set.py):  python3 lupa_layout.py
Writes ready/lupa_layout.json — one entry per Lupa spread (spread 0 = page 1 alone, spread 50 = page 100 alone).
Frames keep each photo's ratio (the plan's no-crop layout), scaled into the theme's margins so the theme art shows.
Full pages, double-page spreads and the map fill their page/spread edge to edge (no frame line).
Photos are matched to Lupa's uploaded images by their EXIF time + shape (Lupa renames files on upload).
"""
import glob
import json
import os
import re

from PIL import Image

SW, SH = 7087, 2551  # Lupa Panoramic Large spread in px (60 x 21.6 cm at 300 dpi)
HALF = 3544
M, FOLD = 235, 200  # theme margin (Lupa's own templates) and inner margin at the fold for single pages
PW = 30.0
SPREAD_BOX = (1.0, 2.4, 58.0, 18.6)  # plan cm boxes (layout_pages.py)
BOX = (1.0, 2.4, 28.0, 18.6)
MAP_FILE = "ready/upload/003_map.jpg"


def key_of(path: str) -> str:
    """EXIF time + shape: how the browser side finds the same photo in Lupa's list."""
    im = Image.open(path)
    t = im.getexif().get_ifd(0x8769).get(0x9003)
    return t.replace(":", "-", 2).replace(" ", "T") + f"|{im.width / im.height:.2f}"


def upload_files() -> dict[tuple[int, str], str]:
    """(photo number, "photo" | "fullpage" | "spread") -> upload file."""
    out = {}
    for f in glob.glob("ready/upload/*_n*.jpg"):
        m = re.search(r"_n(\d{3})(?:_(fullpage|spread|herospread))?\.jpg$", f)
        if m:  # skip QR files whose name happens to contain "_n" (e.g. "_nevada")
            out[(int(m.group(1)), m.group(2) or "photo")] = f
    return out


def place(rects: list[dict], box: tuple, dst: tuple, files: dict, shift: float = 0.0) -> list[dict]:
    """Scale plan rects (cm) from a plan box into a Lupa box (px), same shape, centered."""
    bx, by, bw, bh = box
    dx0, dy0, dx1, dy1 = dst
    s = min((dx1 - dx0) / bw, (dy1 - dy0) / bh)
    ox = dx0 + ((dx1 - dx0) - bw * s) / 2
    oy = dy0 + ((dy1 - dy0) - bh * s) / 2
    out = []
    for r in rects:
        f = r.get("file") or files[(r["n"], "photo")]
        x, y = ox + (r["x"] - shift - bx) * s, oy + (r["y"] - by) * s
        w, h = r["w"] * s, r["h"] * s
        out.append({"n": r["n"], "k": key_of(f), "x": round(x + w / 2), "y": round(y + h / 2), "w": round(w), "h": round(h)})
    return out


def full(path: str, n: int, cx: float, w: int) -> dict:
    """Edge-to-edge frame."""
    return {"n": n, "k": key_of(path), "x": round(cx), "y": SH // 2, "w": w, "h": SH, "bleed": True}


def page_frames(pg: dict, right: bool, files: dict) -> list[dict]:
    """Frames of one single page, in spread px."""
    x0 = HALF - 1 if right else 0
    cx = x0 + HALF / 2
    k = pg["kind"]
    if k in ("hero", "title"):
        n = pg["photos"][0]
        return [full(files[(n, "fullpage")], n, cx, HALF)]
    if k == "map":
        return [full(MAP_FILE, 0, cx, HALF)]
    if not pg.get("rects"):
        return []
    dst = (x0 + FOLD, M, x0 + HALF - M, SH - M) if right else (M, M, HALF - FOLD, SH - M)
    return place(pg["rects"], BOX, dst, files)


SHOWN_TITLES: set[str] = set()


def spread_title(pgs: list[dict], sec_he: dict) -> str:
    """One editable Lupa page title per spread (Lupa allows 45 characters): the places on it, in reading order."""
    import album_config as C
    names: list[str] = []
    for pg in pgs:
        k = pg["kind"]
        if k == "title":
            names.append(f"{C.COVER_TITLE_HE} – {C.COVER_SUB_HE}")
        elif k == "intro":
            names.append(C.INTRO_TITLE_HE)
        elif k == "closing":
            names.append(getattr(C, "CLOSING_TITLE_HE", "סוף הדרך… עד הטיול הבא"))
        elif k in ("photos", "text"):
            if getattr(C, "EXTRA_TITLES", {}).get(pg["no"]):
                names.append(C.EXTRA_TITLES[pg["no"]])
            hidden = getattr(C, "HIDDEN_TITLES", {}).get(pg["no"], [])  # headers the user removed stay out of Lupa too
            names += [sec_he[s] for s in (pg.get("secs") or [pg["sec"]]) if s not in hidden]
    names = [n for n in dict.fromkeys(names) if n not in SHOWN_TITLES]  # never repeat a header
    SHOWN_TITLES.update(names)
    if not names:
        return ""
    t = " · ".join(names)
    if len(t) > 45:  # shorten each place to its first part ("ברייס קניון – מסלול נבאחו" -> "ברייס קניון")
        t = " · ".join(dict.fromkeys(re.split(r" [–-] |, ", n)[0] for n in names))
    return t if len(t) <= 45 else names[0][:45]


def is_qr(f: dict) -> bool:
    """A QR code frame: a small borderless tile that is not a title or a background."""
    return bool(f.get("bleed")) and f["n"] == 0 and f["w"] < HALF - 2 and not f.get("title_tile") and not f.get("texture")


def main() -> None:
    import album_config as C
    """All 51 spreads."""
    plan = json.load(open("plan.json"))
    pages = plan["pages"]
    files = upload_files()
    sec_he = {k: v["he"] for k, v in plan["sections"].items()} if isinstance(plan["sections"], dict) else {x["id"]: x["he"] for x in plan["sections"]}
    spreads = []
    for i in range(len(pages) // 2 + 1):
        if i == 0:
            fr = page_frames(pages[0], False, files)
            sp0 = {"i": 0, "type": "LEFT_TYPE", "pages": [1], "frames": fr}
            ops = getattr(C, "OPENING_PHOTOS", None) or [o for o in [getattr(C, "OPENING_PHOTO", None)] if o]
            if ops:  # photos on Lupa's opening-words page (its own region, right of page 1; local page px)
                sp0["prolog_frames"] = place([{k: o[k] for k in ("n", "x", "y", "w", "h")} for o in ops], BOX,
                                             (FOLD, M, HALF - M, SH - M), files)
                for fr, o in zip(sp0["prolog_frames"], ops):  # exact Lupa position when given (corner placement)
                    if o.get("lupa"):
                        fr["x"], fr["y"], fr["w"], fr["h"] = o["lupa"]
            if getattr(C, "OPENING_BG", None):  # faded photo behind the whole opening-words page
                sp0.setdefault("prolog_frames", []).insert(0, {"n": 0, "k": key_of(C.OPENING_BG), "x": HALF // 2, "y": SH // 2,
                                                                "w": HALF, "h": SH, "bleed": True})
            elif getattr(C, "OPENING_BLANK", False):  # no text on the opening-words page – a white patch under the photos
                sp0.setdefault("prolog_frames", []).insert(0, {"n": 0, "k": key_of("ready/upload/prolog_blank.jpg"),
                                                                "x": 1773, "y": 1228, "w": 1802, "h": 1625, "bleed": True})
            spreads.append(sp0)
            continue
        if i == len(pages) // 2:
            fr = [dict(f, x=f["x"] - (HALF - 1)) for f in page_frames(pages[-1], True, files)]
            spreads.append({"i": i, "type": "RIGHT_TYPE", "pages": [len(pages)], "frames": fr})
            continue
        right, left = pages[2 * i - 1], pages[2 * i]
        if right["kind"] == "spread":
            n = right["photos"][0]
            fr = [dict(full(files[(n, "spread")], n, 3543, SW - 1), h=SH - 1)]
        elif right.get("merged"):
            rects = list(right["rects"])
            th = getattr(C, "TEXT_HALF", {}).get(left.get("sec"), {})
            if left.get("textbox") and th.get("text") and os.path.exists(f"ready/upload/textcard_{left['sec']}.jpg"):
                rects.append({"n": 0, "x": 1.0, "y": 2.4, "w": 13.6, "h": 18.6, "file": f"ready/upload/textcard_{left['sec']}.jpg"})
            fr = place(rects, SPREAD_BOX, (M, M, SW - M, SH - M), files)
        else:
            hero = next((p for p in (right, left) if p["kind"] == "hero"), None)
            face = left if hero is right else right
            if hero and face["kind"] in ("photos", "text", "closing") and (hero["photos"][0], "herospread") in files:
                # blur runs across both pages: one background frame, the facing page's photos on top of it
                bg = dict(full(files[(hero["photos"][0], "herospread")], hero["photos"][0], 3543, SW - 1), h=SH - 1)
                fr = [bg] + page_frames(face, face is right, files)
            else:
                fr = page_frames(right, True, files) + page_frames(left, False, files)
        spreads.append({"i": i, "type": "LAYFLAT_TYPE", "pages": [right["no"], left["no"]], "frames": fr,
                        "solid": right["kind"] == "spread"})
    import album_config as C
    for i, n in getattr(C, "BG_TEXTURES", {}).items():  # texture photo behind the whole spread
        f = f"ready/upload/texbg_s{i:02d}_{n}.jpg"
        spreads[i]["frames"].insert(0, dict(full(f, 0, 3543, SW - 1), h=SH - 1, texture=n))
    for q in getattr(C, "QR_CODES", []):  # QR codes go on top of the page (last frame = painted last)
        i = q["page"] // 2
        right = q["page"] % 2 == 0
        x0 = HALF - 1 if right else 0
        dst = (x0 + FOLD, M, x0 + HALF - M, SH - M) if right else (M, M, HALF - FOLD, SH - M)
        fr = place([{"n": 0, "x": q["x"], "y": q["y"], "w": q["s"], "h": q["s"], "file": q["file"]}], BOX, dst, files)[0]
        if q.get("lupa"):  # exact Lupa centre in spread px (e.g. into the corner, 0.6 cm from the trim)
            fr["x"], fr["y"] = q["lupa"]
        if fr["y"] - fr["h"] / 2 < 59:  # QR codes along the top edge 1 mm lower (code 0.5 cm from the trim)
            fr["y"] += 12
        if spreads[i]["type"] != "LAYFLAT_TYPE":
            fr["x"] -= (HALF - 1) if right else 0
        # QR tiles are always borderless: Lupa themes otherwise add a visible
        # photo frame or shadow around the small cream tile.
        fr["bleed"] = True
        spreads[i]["frames"].append(fr)
    for s in spreads:
        s["title"] = spread_title([pages[n - 1] for n in s["pages"]], sec_he)
        if any(pages[n - 1]["no"] in getattr(C, "TITLE_BOTTOM", set()) for n in s["pages"]):
            s["title_bottom"] = True  # Lupa title strip at the bottom edge of this spread
    # title colour: no box behind text; white on dark backgrounds, near-black on light ones
    path_of = {key_of(f): f for f in set(files.values())}
    from PIL import Image
    for s in spreads:
        if not s.get("title"):
            continue
        cy = SH - 136 if s.get("title_bottom") else 136
        x0, x1, y0, y1 = SW / 2 - 1500, SW / 2 + 1500, cy - 64, cy + 64  # middle of the title strip (text is centred)
        lum = 236.0  # cream page
        for f in s["frames"]:
            fx0, fy0 = f["x"] - f["w"] / 2, f["y"] - f["h"] / 2
            if f.get("n", 1) == 0 or f["k"] not in path_of or fx0 > x0 or fx0 + f["w"] < x1 or fy0 > y0 or fy0 + f["h"] < y1:
                continue  # only a photo/background that covers the whole title area counts
            im = Image.open(path_of[f["k"]]).convert("L")
            W_, H_ = im.size
            band = im.crop((int((x0 - fx0) / f["w"] * W_), int((y0 - fy0) / f["h"] * H_),
                            int((x1 - fx0) / f["w"] * W_), int((y1 - fy0) / f["h"] * H_)))
            h = band.histogram(); lum = sum(i * c for i, c in enumerate(h)) / max(1, sum(h))
        s["title_ink"] = "dark" if lum > 140 else "light"
    keys = [f["k"] for s in spreads for f in s["frames"] + s.get("prolog_frames", [])]
    assert len(keys) == len(set(keys)), "two frames point at the same photo"
    for s in spreads:  # QR codes always the top layer (painted last), above photos, titles and frame lines
        qr = [f for f in s["frames"] if is_qr(f)]
        s["frames"] = [f for f in s["frames"] if not is_qr(f)] + qr
    json.dump({"W": SW, "H": SH, "spreads": spreads}, open("ready/lupa_layout.json", "w"), indent=0)
    print("Next: python3 check_book.py (QR codes must not cross a photo's edge)")
    print(f"{len(spreads)} spreads, {len(keys)} frames "
          f"({sum(1 for s in spreads for f in s['frames'] if f.get('bleed'))} edge-to-edge), "
          f"{os.path.getsize('ready/lupa_layout.json') // 1024} KB")


if __name__ == "__main__":
    main()
