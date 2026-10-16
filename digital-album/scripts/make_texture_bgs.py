"""Full-spread backgrounds from the user's texture photos (album_config.BG_TEXTURES, ).

A texture fills the whole spread (60 x 21.6 cm, 7087 x 2551 px). Textures may be trimmed to fit (they are
backgrounds, not photos of the trip), and enhanced (clarity, detail, saturation) so they look alive in print.
Writes ready/upload/texbg_sNN_PPP.jpg. Usage (album folder):  python3 make_texture_bgs.py
"""
import json
import os
import subprocess
from datetime import timedelta

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

import album_config as C
import make_upload_set as U

SW, SH = 7087, 2551


def enhance(im: Image.Image) -> Image.Image:
    """Make a texture look alive and real in print: local contrast ("clarity"), detail, colour."""
    im = im.filter(ImageFilter.UnsharpMask(radius=80, percent=18, threshold=0))   # clarity: big-radius local contrast
    im = im.filter(ImageFilter.UnsharpMask(radius=1.5, percent=25, threshold=4))    # fine detail
    im = ImageEnhance.Contrast(im).enhance(1.05)
    im = ImageEnhance.Color(im).enhance(1.15)                                     # saturation
    return ImageEnhance.Brightness(im).enhance(1.02)


def main() -> None:
    photos = {p["n"]: p for p in json.load(open("plan.json"))["photos"]}
    used = {}
    for i, n in sorted(getattr(C, "BG_TEXTURES", {}).items()):
        p = photos[n]
        dup = used.get(n, 0)  # same photo behind a second spread: its own EXIF second, so Lupa keeps two files
        used[n] = dup + 1
        src = f"originals/{n}.jpg"
        if not os.path.exists(src):
            subprocess.run(["curl", "-s", "-o", src, p["url"] + "=d"], check=True, timeout=300)
        im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
        im = ImageOps.fit(im, (SW, SH), Image.LANCZOS)
        im = enhance(im)
        fade = getattr(C, "BG_TEXTURE_FADE", {}).get(i, 0)
        if fade:  # lighter background: blend toward white paper
            im = Image.blend(im, Image.new("RGB", im.size, (255, 255, 255)), fade)
        out = f"ready/upload/texbg_s{i:02d}_{n}.jpg"
        U.save_with_time(im, out, U.stamp(p) + timedelta(seconds=dup + (7 if fade else 0)), quality=90)
        print(out)


if __name__ == "__main__":
    main()
