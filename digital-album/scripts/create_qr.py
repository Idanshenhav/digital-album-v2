#!/usr/bin/env python3
"""Create the approved compact Option 1 QR-code JPEG."""

from __future__ import annotations

import argparse
import re
import unicodedata
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw


BACKGROUND = "#F7F4EC"
INK = "#173F35"
BOX_SIZE = 28
BORDER = 4


def location_slug(location: str) -> str:
    normalized = unicodedata.normalize("NFKD", location)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-")
    if not slug:
        raise ValueError("Location needs at least one transliterable ASCII character for the filename")
    return slug


def next_available(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f"{path.stem}-{index:02d}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Could not find an available filename for {path.name}")


def draw_finder(draw: ImageDraw.ImageDraw, x: int, y: int) -> None:
    """Lightly rounded corner marker. Rounder markers failed scan tests, so keep these radii small."""
    size = 7 * BOX_SIZE
    draw.rectangle((x, y, x + size - 1, y + size - 1), fill=BACKGROUND)  # clear the square dots underneath
    draw.rounded_rectangle((x, y, x + size - 1, y + size - 1), radius=int(0.6 * BOX_SIZE), fill=INK)
    draw.rounded_rectangle(
        (x + BOX_SIZE, y + BOX_SIZE, x + 6 * BOX_SIZE - 1, y + 6 * BOX_SIZE - 1), radius=int(0.4 * BOX_SIZE), fill=BACKGROUND
    )
    draw.rounded_rectangle(
        (x + 2 * BOX_SIZE, y + 2 * BOX_SIZE, x + 5 * BOX_SIZE - 1, y + 5 * BOX_SIZE - 1), radius=int(0.25 * BOX_SIZE), fill=INK
    )


def round_tile(image: Image.Image) -> Image.Image:
    """Round the tile's outer corners. Returns RGBA with transparent corners (for the PNG placed on photos)."""
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, image.width - 1, image.height - 1), radius=2 * BOX_SIZE, fill=255)
    tile = image.convert("RGBA")
    tile.putalpha(mask)
    return tile


def verify(path: Path, url: str) -> None:
    """Decode the saved file at full size and at ~2 cm print size (236 px); stop if either fails."""
    import cv2
    import numpy as np

    detectors = [cv2.QRCodeDetector(), cv2.QRCodeDetectorAruco()]
    image = Image.open(path).convert("RGBA")
    for px in (image.width, 236):
        sample = Image.new("RGB", (px + 40, px + 40), "white")
        small = image.resize((px, px), Image.LANCZOS)
        sample.paste(small, (20, 20), small)
        array = cv2.cvtColor(np.array(sample), cv2.COLOR_RGB2BGR)
        if not any(d.detectAndDecode(array)[0] == url for d in detectors):
            raise SystemExit(f"SCAN FAILED for {path.name} at {px}px")
    print(f"scan_ok={path.name}")


def build_qr(url: str) -> Image.Image:
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=1,
        border=BORDER,
    )
    qr.add_data(url)
    qr.make(fit=True)
    matrix = qr.get_matrix()
    size = len(matrix)
    image = Image.new("RGB", (size * BOX_SIZE, size * BOX_SIZE), BACKGROUND)
    draw = ImageDraw.Draw(image)
    for row, values in enumerate(matrix):
        for col, active in enumerate(values):
            if active:
                x, y = col * BOX_SIZE, row * BOX_SIZE
                draw.rounded_rectangle(
                    (x + 2, y + 2, x + BOX_SIZE - 3, y + BOX_SIZE - 3),
                    radius=6,
                    fill=INK,
                )
    draw_finder(draw, BORDER * BOX_SIZE, BORDER * BOX_SIZE)
    draw_finder(draw, (size - BORDER - 7) * BOX_SIZE, BORDER * BOX_SIZE)
    draw_finder(draw, BORDER * BOX_SIZE, (size - BORDER - 7) * BOX_SIZE)
    return image


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--date", required=True, help="Date taken in YYYY-MM-DD format")
    parser.add_argument("--location", required=True)
    parser.add_argument(
        "--output-root",
        default=".",
        help="Album folder (default: the current folder); files go to <album>/qr-codes/",
    )
    args = parser.parse_args()

    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", args.date):
        raise SystemExit("--date must use YYYY-MM-DD format")
    if not re.match(r"^https?://", args.url):
        raise SystemExit("--url must be an http(s) URL")

    output_dir = Path(args.output_root).expanduser().resolve() / "qr-codes"
    output_dir.mkdir(parents=True, exist_ok=True)
    requested = output_dir / f"{args.date}_{location_slug(args.location)}.jpg"
    output = next_available(requested)
    image = build_qr(args.url)
    tile = round_tile(image)
    jpeg = Image.new("RGB", tile.size, "white")  # JPEG has no transparency: corners become white
    jpeg.paste(tile, mask=tile.getchannel("A"))
    jpeg.save(output, format="JPEG", quality=96, subsampling=0, optimize=True)
    png = output.with_suffix(".png")  # transparent corners, for placing on a photo
    tile.save(png)
    verify(output, args.url)
    verify(png, args.url)
    print(f"output={output}")
    print(f"png={png}")
    print(f"dimensions={image.width}x{image.height}")


if __name__ == "__main__":
    main()
