"""Front cover photo: cut to the cover shape (full height, no margins) and tuned only, never generated.

Sky: bluer and more dramatic (deeper blue, more cloud contrast). People: shadows lifted in a soft region.
Settings in album_config.py: COVER_SRC (full-size photo or RAW export), COVER_RATIO (the editor's cover photo
shape, Lupa Panoramic Large = 3900/2860), COVER_LEFT (px cut on the left; the rest comes off the right, so the
sky gap lands under the title), COVER_PEOPLE (x0, y0, x1, y1 fractions of the people), COVER_SKY (saturation,
deepen, cloud contrast), COVER_PHOTO_STAMP. Writes ready/upload/000_cover.jpg; make_cover_title.py adds the title.
Usage (album folder):  python3 make_cover_photo.py
"""
from datetime import datetime

import numpy as np
from PIL import Image, ImageFilter

import make_upload_set as U
from prepare_originals import lift_shadows

import album_config as C

SRC = C.COVER_SRC
OUT = getattr(C, "COVER_PHOTO_FILE", "ready/upload/000_cover.jpg")
RATIO = getattr(C, "COVER_RATIO", 3900 / 2860)
LEFT = getattr(C, "COVER_LEFT", None)  # None = cut evenly from both sides
FAMILY = getattr(C, "COVER_PEOPLE", (0.30, 0.52, 0.80, 1.02))  # soft region for the shadow lift
SKY_SAT, SKY_DEEPEN, CLOUD_CONTRAST = getattr(C, "COVER_SKY", (1.55, 0.86, 1.25))


def sky_mask(a: np.ndarray) -> np.ndarray:
    """1 on blue sky and clouds in the upper part, 0 on cliffs, trees and people."""
    h, w, _ = a.shape
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lum = a @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    m = np.clip((b - r - 0.015) / 0.05, 0, 1) * np.clip((lum - 0.45) / 0.1, 0, 1)
    rows = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    m = m * np.clip((0.5 - rows) / 0.1, 0, 1)
    im = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)).filter(ImageFilter.GaussianBlur(6))
    return np.asarray(im, dtype=np.float32) / 255


def tune_sky(im: Image.Image) -> Image.Image:
    """Deeper, more saturated blue; brighter clouds against it."""
    a = np.asarray(im, dtype=np.float32) / 255
    m = sky_mask(a)[..., None]
    lum = (a @ np.array([0.299, 0.587, 0.114], dtype=np.float32))[..., None]
    sat = lum + (a - lum) * SKY_SAT
    blueness = np.clip((a[..., 2:3] - a[..., 0:1]) / 0.25, 0, 1)  # clear blue gets deepened, white cloud less
    deep = sat * (1 - (1 - SKY_DEEPEN) * blueness)
    mid = 0.72
    contrast = np.clip(mid + (deep - mid) * CLOUD_CONTRAST, 0, 1)
    out = a * (1 - m) + contrast * m
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8))


def main() -> None:
    im = Image.open(SRC).convert("RGB")
    w, h = im.size
    cw = round(h * RATIO)
    left = (w - cw) // 2 if LEFT is None else LEFT
    im = im.crop((left, 0, left + cw, h))
    im = lift_shadows(im, 70, FAMILY)
    im = tune_sky(im)
    U.save_with_time(im, OUT, getattr(C, "COVER_PHOTO_STAMP", datetime(2001, 1, 3, 7, 0, 0)), quality=95)
    print(OUT, im.size)


if __name__ == "__main__":
    main()
