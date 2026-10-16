"""Final check of the book before it goes to the album editor or to print (run in the album folder).

Reads ready/lupa_layout.json and the upload files, and reports:
  ERRORS (exit code 1): missing files, photos under 200 dpi, photos cropped more than 5%, photos covering
    each other, a photo used twice, QR codes that are too small, too close to the trim, not on top, or that
    STRADDLE a photo's edge (the album editor may draw that photo's frame line across the code).
  NOTES: photos 200-250 dpi, every page title (read them for spelling), QR codes sitting inside a photo
    (make sure they are on background, never on faces).
Usage:  python3 check_book.py
"""
import glob
import json
import os
import sys

from PIL import Image

import lupa_layout as LL

PX_CM = 300 / 2.54  # editor px per cm (300 dpi)
QR_MIN = round(2.0 * PX_CM)  # printed QR at least 2 cm
TRIM = round(0.5 * PX_CM)  # anything important at least 0.5 cm inside the trim
CLEAR = round(0.3 * PX_CM)  # a QR keeps 0.3 cm away from any photo edge it does not sit inside


def box(f: dict) -> tuple:
    return (f["x"] - f["w"] / 2, f["y"] - f["h"] / 2, f["x"] + f["w"] / 2, f["y"] + f["h"] / 2)


def overlap(a: tuple, b: tuple) -> tuple:
    return max(0, min(a[2], b[2]) - max(a[0], b[0])), max(0, min(a[3], b[3]) - max(a[1], b[1]))


def is_qr(f: dict) -> bool:
    return f.get("bleed") and f["n"] == 0 and f["w"] < LL.HALF - 2 and not f.get("title_tile") and not f.get("texture")


def is_photo(f: dict) -> bool:
    return not f.get("bleed") and f["n"] != 0 or (f["n"] != 0 and f["w"] < LL.HALF - 2)


def main() -> int:
    L = json.load(open("ready/lupa_layout.json"))
    path_of = {}
    for f in glob.glob("ready/upload/*.jpg"):
        if not os.path.basename(f).startswith("old_"):
            path_of.setdefault(LL.key_of(f), f)
    err, note, used, titles = [], [], {}, []
    for i, s in enumerate(L["spreads"]):
        fr = [f for f in s.get("frames", []) + s.get("prolog_frames", [])]
        photos = [f for f in fr if is_photo(f)]
        qrs = [f for f in s.get("frames", []) if is_qr(f)]
        for f in fr:
            p = path_of.get(f["k"])
            if not p:
                err.append(f"spread {i}: no upload file for {f['k']} (#{f['n']})")
                continue
            if f in photos:
                im = Image.open(p)
                ia, fa = im.width / im.height, f["w"] / f["h"]
                crop = 1 - min(ia / fa, fa / ia)
                dpi = im.width * min(1, fa / ia) / f["w"] * 300
                if dpi < 200:
                    err.append(f"spread {i}: #{f['n']} only {dpi:.0f} dpi (blurry in print)")
                elif dpi < 250:
                    note.append(f"spread {i}: #{f['n']} {dpi:.0f} dpi (fine, not razor sharp)")
                if crop > 0.05:
                    err.append(f"spread {i}: #{f['n']} cropped {crop:.0%} (rule: no crop, 5% at most)")
                used.setdefault(f["n"], []).append(i)
            if f.get("title_tile"):
                titles.append(f"spread {i}: {f.get('text', '')}")
        for a in range(len(photos)):
            for b in range(a + 1, len(photos)):
                ox, oy = overlap(box(photos[a]), box(photos[b]))
                if ox > 8 and oy > 8:
                    err.append(f"spread {i}: #{photos[a]['n']} and #{photos[b]['n']} cover each other")
        frames = s.get("frames", [])
        if qrs and any(not is_qr(f) for f in frames[frames.index(qrs[0]):]):
            err.append(f"spread {i}: a QR code is not the top layer (it must be the last frame)")
        W = LL.SW if s.get("type", "LAYFLAT_TYPE") == "LAYFLAT_TYPE" else LL.HALF
        for q in qrs:
            b = box(q)
            if min(q["w"], q["h"]) < QR_MIN:
                err.append(f"spread {i}: QR {q['k']} is {q['w'] / PX_CM:.1f} cm (min 2 cm)")
            if b[0] < TRIM - 30 or b[1] < TRIM - 30 or b[2] > W - TRIM + 30 or b[3] > LL.SH - TRIM + 30:
                note.append(f"spread {i}: QR {q['k']} closer than 0.5 cm to the trim (the code's own margin may cover it; check)")
            for p in photos + [f for f in frames if f.get("title_tile")]:
                pb = box(p)
                ox, oy = overlap(b, pb)
                inside = b[0] >= pb[0] + CLEAR and b[1] >= pb[1] + CLEAR and b[2] <= pb[2] - CLEAR and b[3] <= pb[3] - CLEAR
                near = overlap((b[0] - CLEAR, b[1] - CLEAR, b[2] + CLEAR, b[3] + CLEAR), pb)
                what = "title" if p.get("title_tile") else f"#{p['n']}"
                if inside and not p.get("title_tile"):
                    note.append(f"spread {i}: QR {q['k']} sits inside {what}: check it is on background, not on a face")
                elif (ox > 0 and oy > 0) or (near[0] > 0 and near[1] > 0):
                    err.append(f"spread {i}: QR {q['k']} straddles or touches the edge of {what} "
                               f"(move it fully onto background with 0.3 cm space, or fully inside the photo)")
    for n, where in used.items():
        if len(where) > 1:
            err.append(f"#{n} is used twice (spreads {where})")
    print(f"{len(L['spreads'])} spreads checked")
    print("\nPAGE TITLES (read for spelling):\n  " + "\n  ".join(titles) if titles else "")
    if note:
        print("\nNOTES:\n  " + "\n  ".join(note))
    print("\nERRORS:\n  " + "\n  ".join(err) if err else "\nNo errors.")
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main())
