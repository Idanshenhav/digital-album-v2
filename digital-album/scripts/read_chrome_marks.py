"""Read the review marks the user made in the HTML plan, straight from Chrome's saved page data.

Usage:  python3 read_chrome_marks.py <STORE_KEY>        e.g. usa2021-album-marks-r2

The plan page saves marks in the browser (localStorage) under STORE_KEY. When the plan was opened
from disk in Chrome, that data sits in Chrome's profile folder. This script only looks for that one
key and prints the newest value as a ready-to-paste list plus Python for album_config.py.
Prefer asking for the "Copy my marks" text when it's easy — this is the fallback.
"""
import glob
import json
import os
import re
import sys


def main() -> None:
    """Print the newest saved marks for the key."""
    key = sys.argv[1].encode()
    base = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    newest, when = None, 0.0
    # .ldb = older compacted data, .log = newest writes (appended in order), so read .ldb first and let .log win
    files = sorted(glob.glob(f"{base}/*/Local Storage/leveldb/*.ldb")) + sorted(glob.glob(f"{base}/*/Local Storage/leveldb/*.log"))
    for order, f in enumerate(files):
        b = open(f, "rb").read()
        for m in re.finditer(re.escape(key) + rb"(?![\w-])", b):  # exact key, not a longer key that starts the same
            seg = b[m.end():m.end() + 20000]
            i = seg.find(b"{")
            txt = seg[i:].decode("latin-1", "ignore")
            depth, end = 0, 0
            for k, ch in enumerate(txt):
                depth += ch == "{"
                depth -= ch == "}"
                if depth == 0 and ch == "}":
                    end = k + 1
                    break
            try:
                val = json.loads(txt[:end])
            except ValueError:
                continue  # compressed block in .ldb, skip
            t = order * 1e9 + m.start()  # later file, later position = newer
            if t >= when:
                newest, when = val, t
    if newest is None:
        sys.exit("No marks found — ask for the 'Copy my marks' text instead.")
    rep = {int(n): int(m["with"]) for n, m in newest.items() if m["kind"] == "replace" and m.get("with")}
    rem = [int(n) for n, m in newest.items() if m["kind"] == "replace" and not m.get("with")]
    swaps = [(int(n), int(m["with"])) for n, m in newest.items() if m["kind"] == "swap"]
    add = [int(n) for n, m in newest.items() if m["kind"] == "add"]
    notes = {int(n): m["note"] for n, m in newest.items() if m.get("note")}
    print(f"{len(newest)} marks\nREPLACE = {rep}\nREMOVE (no replacement) = {rem}\nSWAPS = {swaps}\nADD_BACK = {add}\nNOTES = {notes}")


if __name__ == "__main__":
    main()
