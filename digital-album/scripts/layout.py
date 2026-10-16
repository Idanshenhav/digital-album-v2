"""Crop-free page layouts: every photo keeps its original aspect ratio.

Photos are arranged as a "guillotine" tree of rows (H) and columns (V). For a node,
width = a * height + b holds exactly (b carries the gaps), so any tree can be scaled
to fit the page box without cropping. We try all trees (and small reorderings) and
keep the one that covers the page best while keeping photo sizes balanced.
"""
from functools import lru_cache
from itertools import permutations
from typing import Any

GAP = 0.4  # cm between photos
MAX_TRIM = 0.05  # a frame may trim at most 5% off one side of a photo, to close wide margins
BIGGER: list[tuple[int, int]] = []  # (a, b): when both are laid out together, photo a must get the bigger frame


def _combos(aspects: tuple[float, ...]) -> list[tuple[float, float, Any]]:
    """All (a, b, tree) for an ordered tuple of photo aspects."""
    return list(_combos_c(aspects))


@lru_cache(maxsize=200000)
def _combos_c(aspects: tuple[float, ...]) -> tuple[tuple[float, float, Any], ...]:
    if len(aspects) == 1:
        return ((aspects[0], 0.0, 0),)
    out = []
    for k in range(1, len(aspects)):
        for a1, b1, t1 in _combos_c(aspects[:k]):
            for a2, b2, t2 in _combos_c(aspects[k:]):
                # side by side (same height)
                out.append((a1 + a2, b1 + b2 + GAP, ("H", k, t1, t2)))
                # stacked (same width)
                inv = 1 / a1 + 1 / a2
                a = 1 / inv
                out.append((a, a * (b1 / a1 + b2 / a2 - GAP), ("V", k, t1, t2)))
    # keep the list small: drop near-identical shapes
    out.sort(key=lambda x: (round(x[0], 3), round(x[1], 2)))
    dedup, last = [], None
    for x in out:
        key = (round(x[0], 3), round(x[1], 2))
        if key != last:
            dedup.append(x)
            last = key
    return tuple(dedup)


def _place(tree: Any, aspects: list[float], idx: list[int], x: float, y: float, w: float, h: float,
           out: list[tuple[int, float, float, float, float]]) -> None:
    """Assign rectangles for a tree inside box (x, y, w, h)."""
    if tree == 0:
        out.append((idx[0], x, y, w, h))
        return
    kind, k, t1, t2 = tree
    a1, b1 = _ab(t1, aspects[:k])
    a2, b2 = _ab(t2, aspects[k:])
    if kind == "H":
        w1 = a1 * h + b1
        _place(t1, aspects[:k], idx[:k], x, y, w1, h, out)
        _place(t2, aspects[k:], idx[k:], x + w1 + GAP, y, w - w1 - GAP, h, out)
    else:
        h1 = (w - b1) / a1
        _place(t1, aspects[:k], idx[:k], x, y, w, h1, out)
        _place(t2, aspects[k:], idx[k:], x, y + h1 + GAP, w, h - h1 - GAP, out)


def _ab(tree: Any, aspects: list[float]) -> tuple[float, float]:
    """(a, b) of a given tree."""
    if tree == 0:
        return aspects[0], 0.0
    kind, k, t1, t2 = tree
    a1, b1 = _ab(t1, aspects[:k])
    a2, b2 = _ab(t2, aspects[k:])
    if kind == "H":
        return a1 + a2, b1 + b2 + GAP
    a = 1 / (1 / a1 + 1 / a2)
    return a, a * (b1 / a1 + b2 / a2 - GAP)


def best_layout(items: list[tuple[int, float]], W: float, H: float, x0: float = 0, y0: float = 0,
                keep_order_bonus: float = 0.02) -> dict[str, Any]:
    """Best crop-free layout of photos [(n, aspect)] in a W x H box (cm)."""
    n = len(items)
    orders = [tuple(range(n))]
    if n <= 5:
        orders = list(permutations(range(n)))
    elif n == 6:
        orders = [tuple(range(6))] + [p for p in permutations(range(6)) if p[:2] in ((0, 1), (1, 0))][:120]
    best, best_any = None, None
    for order in orders:
        asp = tuple(round(items[i][1], 4) for i in order)
        for a, b, tree in _combos(asp):
            h = min(H, (W - b) / a)
            w = a * h + b
            if h <= 0 or w <= 0:
                continue
            rects: list[tuple[int, float, float, float, float]] = []
            _place(tree, list(asp), list(order), 0, 0, w, h, rects)
            areas = [r[3] * r[4] for r in rects]
            fill = sum(areas) / (W * H)
            balance = min(areas) / max(areas)
            min_long = min(max(r[3], r[4]) for r in rects)
            score = fill * (0.55 + 0.45 * balance ** 0.5) * (1 if min_long >= 7 else 0.8) + (keep_order_bonus if order == tuple(range(n)) else 0)
            cand = (score, w, h, rects, fill, balance)
            if best_any is None or score > best_any[0]:
                best_any = cand
            area = {items[r[0]][0]: r[3] * r[4] for r in rects}
            if any(a in area and b in area and area[a] <= area[b] for a, b in BIGGER):
                continue
            if best is None or score > best[0]:
                best = cand
    score, w, h, rects, fill, balance = best or best_any
    sx = min(W / w, 1 + MAX_TRIM) if w < W else 1.0
    sy = min(H / h, 1 + MAX_TRIM) if h < H else 1.0
    rects = [(i, x * sx, y * sy, rw * sx, rh * sy) for i, x, y, rw, rh in rects]
    w, h = w * sx, h * sy
    fill = sum(r[3] * r[4] for r in rects) / (W * H)
    ox, oy = x0 + (W - w) / 2, y0 + (H - h) / 2  # center the block on the page
    return {
        "rects": [{"n": items[i][0], "x": round(ox + x, 2), "y": round(oy + y, 2), "w": round(rw, 2), "h": round(rh, 2)}
                  for i, x, y, rw, rh in rects],
        "fill": round(fill, 3), "balance": round(balance, 3),
    }


if __name__ == "__main__":
    import time
    t = time.time()
    print(best_layout([(1, 16 / 9), (2, 16 / 9), (3, 9 / 16), (4, 4 / 3), (5, 16 / 9)], 28, 18.8))
    print(round(time.time() - t, 2), "s")
