"""Find cameras whose clock was wrong, so the album order can follow real time.

Usage (album folder, after the review notes exist):  python3 clock_check.py

Groups photos by camera "signature" (megapixels + the timezone Google stored). For each group
it tests clock shifts from -12h to +12h and counts how many photos then land next to photos of
the SAME place (from notes/part*.json). The best shift is the one with the most matches.
It also looks for exact duplicate shots across cameras (same picture copied from another phone)
— their time difference gives the offset exactly. Put the result into CLOCK_FIXES in album_config.py.
"""
import bisect
import collections
import glob
import json

import numpy as np
from PIL import Image

HOUR = 3600000


def key(place: str) -> str:
    """Rough place key for matching neighbours."""
    return place.split("–")[0].split("(")[0].strip().rstrip("?").lower()[:14]


def dhash(n: int) -> np.ndarray:
    """64-bit difference hash of a preview."""
    g = np.asarray(Image.open(f"thumbs/{n:03d}.jpg").convert("L").resize((9, 8)), dtype=float)
    return (g[:, 1:] > g[:, :-1]).flatten()


def main() -> None:
    """Print suggested CLOCK_FIXES."""
    rows = json.load(open("items.json"))
    notes = {x["n"]: x for f in glob.glob("notes/part*.json") for x in json.load(open(f))}
    groups = collections.defaultdict(list)
    for r in rows:
        groups[(r["mp"], (r["tz"] or 0) / HOUR)].append(r)
    tz_count = collections.Counter((r["tz"] or 0) / HOUR for r in rows)
    print("timezones Google stored (hours):", dict(tz_count))
    hashes = {r["n"]: dhash(r["n"]) for r in rows}
    for (mp, tz), g in sorted(groups.items(), key=lambda x: -len(x[1])):
        if len(g) < 3:
            continue
        others = sorted([r for r in rows if r not in g], key=lambda r: r["ts"])
        ots = [r["ts"] for r in others]
        scores = []
        for h in [x / 2 for x in range(-24, 25)]:
            good = 0
            for c in g:
                i = bisect.bisect(ots, c["ts"] + h * HOUR)
                nb = [others[j] for j in (i - 1, i) if 0 <= j < len(others)]
                good += any(key(notes[o["n"]]["place"]) == key(notes[c["n"]]["place"]) for o in nb)
            scores.append((good, -abs(h), h))
        best = max(scores)
        zero = next(s for s in scores if s[2] == 0)
        flag = "  <-- clock looks wrong" if best[0] > zero[0] + max(2, len(g) // 10) else ""
        plateau = [s[2] for s in scores if s[0] >= best[0]]
        rng = f" (equally good {min(plateau):+}..{max(plateau):+}h, middle {(min(plateau) + max(plateau)) / 2:+}h)" if flag else ""
        print(f"camera {mp}MP tz {tz:+}h: {len(g)} photos | no shift: {zero[0]} matches | best shift {best[2]:+}h: {best[0]} matches{flag}{rng}")
    # exact duplicates across different cameras / timezones -> exact offset
    for a in rows:
        for b in rows:
            if a["n"] < b["n"] and (a["mp"], a["tz"]) != (b["mp"], b["tz"]) and (hashes[a["n"]] != hashes[b["n"]]).sum() <= 3:
                print(f"same shot: #{a['n']} and #{b['n']} differ by {(b['ts'] - a['ts']) / HOUR:+.2f}h")


if __name__ == "__main__":
    main()
