"""Give a new EXIF time to every upload file whose picture changed but kept its old time.

Lupa matches uploads by EXIF time + shape. A re-made file (title, QR tile, background, full page…) with the
same time is silently ignored: the book keeps showing the OLD picture. This script remembers each file's
picture (a small pixel fingerprint) in ready/stamps.json. When a file's picture changed but its time did not,
it moves the time forward one hour at a time to the first unused time, and points ready/lupa_layout.json at it.

Run after every rebuild, before uploading:  python3 restamp_tiles.py
"""
import glob
import hashlib
import json
import os
from datetime import datetime, timedelta

from PIL import Image

import lupa_layout as LL
import make_upload_set as U

STATE = "ready/stamps.json"
VERSION = 3  # bump when fingerprint() changes: older states are re-recorded, never acted on


def fingerprint(path: str) -> str:
    """Pixel fingerprint that ignores JPEG re-encoding noise."""
    im = Image.open(path).convert("RGB").resize((24, 24), Image.BOX)
    return hashlib.sha1(bytes((v + 8) // 16 for v in im.tobytes())).hexdigest()


def main() -> None:
    """Restamp changed files, update the layout keys, save the new fingerprints."""
    saved = json.load(open(STATE)) if os.path.exists(STATE) else {}
    state = saved.get("files", {}) if saved.get("version") == VERSION else {}  # first run: just record
    files = [f for f in glob.glob("ready/upload/*.jpg") if not os.path.basename(f).startswith("old_")]
    keys = {f: LL.key_of(f) for f in files}
    used = {k.split("|")[0] for k in keys.values()} | {k.split("|")[0] for v in state.values() for k in v.get("seen", {})}
    L = json.load(open("ready/lupa_layout.json")) if os.path.exists("ready/lupa_layout.json") else None
    changed = []
    for f in sorted(files):
        name, key, fp = os.path.basename(f), keys[f], fingerprint(f)
        seen = state.get(name, {}).get("seen", {})  # every time this file has had -> its picture then
        if key in seen and seen[key] != fp:  # new picture, a time Lupa already saw -> Lupa would show the old one
            t = datetime.strptime(key.split("|")[0], "%Y-%m-%dT%H:%M:%S")
            while t.strftime("%Y-%m-%dT%H:%M:%S") in used:
                t += timedelta(hours=1)
            U.save_with_time(Image.open(f).convert("RGB"), f, t, quality=95)
            new = LL.key_of(f)
            used.add(new.split("|")[0])
            if L:
                for s in L["spreads"]:
                    for fr in s.get("frames", []) + s.get("prolog_frames", []):
                        if fr["k"] == key:
                            fr["k"] = new
            changed.append(f"{name}: {key} -> {new}")
            key, fp = new, fingerprint(f)
        seen[key] = fp
        state[name] = {"key": key, "fp": fp, "seen": seen}
    if L:
        json.dump(L, open("ready/lupa_layout.json", "w"))
    json.dump({"version": VERSION, "files": state}, open(STATE, "w"), indent=0)
    dup = {}
    for f, k in keys.items():
        dup.setdefault(k, []).append(os.path.basename(f))
    clash = [v for v in dup.values() if len(v) > 1]
    print(f"{len(changed)} file(s) restamped" + ("".join(f"\n  {c}" for c in changed)))
    if clash:
        print("WARNING: files sharing one time+shape (Lupa can't tell them apart):", clash)


if __name__ == "__main__":
    main()
