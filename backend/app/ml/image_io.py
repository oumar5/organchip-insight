"""Decode single-plane microscopy images without clipping unsigned 16-bit data."""

from pathlib import Path

import numpy as np
from PIL import Image

DEFAULT_MAX_IMAGE_PIXELS = 16_777_216


def validate_image(source: Image.Image, max_pixels: int = DEFAULT_MAX_IMAGE_PIXELS) -> None:
    if source.format not in {"PNG", "JPEG", "TIFF"}:
        raise ValueError("Format réel non pris en charge : PNG, JPEG ou TIFF attendu.")
    if source.width * source.height > max_pixels:
        raise ValueError(f"Image trop grande : limite de {max_pixels:,} pixels.")
    if getattr(source, "n_frames", 1) != 1:
        raise ValueError("Les images multipages doivent être exportées en plans séparés.")
    if source.mode not in {
        "1",
        "L",
        "LA",
        "P",
        "RGB",
        "RGBA",
        "CMYK",
        "I;16",
        "I;16L",
        "I;16B",
        "I",
    }:
        raise ValueError("Seuls les pixels entiers 8 ou 16 bits sont pris en charge.")
    source.load()  # verify() alone does not decode JPEG/TIFF pixel data.
    if source.mode == "I":
        values = np.asarray(source)
        if values.min() < 0 or values.max() > 65535:
            raise ValueError("Les intensités entières doivent être comprises entre 0 et 65535.")


def read_image(
    path: Path, max_pixels: int = DEFAULT_MAX_IMAGE_PIXELS
) -> tuple[np.ndarray, np.ndarray]:
    with Image.open(path) as source:
        validate_image(source, max_pixels)
        if source.mode.startswith("I"):
            grayscale = np.asarray(source, dtype=np.float32) / 65535.0
            display = np.rint(grayscale * 255).astype(np.uint8)
            rgb = np.repeat(display[:, :, None], 3, axis=2)
        else:
            # Preserve the historical 8-bit benchmark preprocessing exactly.
            rgb = np.asarray(source.convert("RGB"), dtype=np.uint8)
            grayscale = np.asarray(source.convert("L"), dtype=np.float32) / 255.0
    return rgb, grayscale
