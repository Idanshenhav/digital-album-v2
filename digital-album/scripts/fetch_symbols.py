"""Download one cartoon symbol per place: Noto Animated Emoji by Google (CC BY 4.0), 512 px PNG.

Usage (album folder):  python3 fetch_symbols.py
Reads EMO from album_config.py: {"S03": "1f98c", ...} (section id -> emoji code point, lowercase hex).
Each symbol must be used only once in the book, so the code points must be unique.
Browse code points at https://googlefonts.github.io/noto-emoji-animation/
Writes symbols/emoji/<section>.png and symbols/emoji/map.json (read by make_html.py).
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.getcwd())
from album_config import EMO  # noqa: E402


def main() -> None:
    """Fetch all symbols; code points that need the emoji variation selector get _fe0f."""
    assert len(set(EMO.values())) == len(EMO), "each symbol once: duplicate code points in EMO"
    os.makedirs("symbols/emoji", exist_ok=True)
    bad = []
    for sec, cp in EMO.items():
        for c in (cp, cp + "_fe0f"):
            r = subprocess.run(["curl", "-s", "-o", f"symbols/emoji/{sec}.png", "-w", "%{http_code} %{content_type}",
                                f"https://fonts.gstatic.com/s/e/notoemoji/latest/{c}/512.png"], capture_output=True, text=True)
            if r.stdout.startswith("200 image"):
                break
        else:
            bad.append((sec, cp))
    json.dump(EMO, open("symbols/emoji/map.json", "w"))
    print(f"{len(EMO) - len(bad)} symbols saved; failed: {bad}")


if __name__ == "__main__":
    main()
