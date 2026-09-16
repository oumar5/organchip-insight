from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.ml.image_io import read_image
from app.ml.pipeline import AdaptiveSegmentationAnalyzer


@pytest.mark.parametrize("dtype", ["<u2", ">u2"])
def test_16_bit_tiff_preserves_8_bit_equivalent_segmentation(tmp_path: Path, dtype: str):
    pixels = np.full((128, 128), 20, dtype=np.uint8)
    pixels[40:80, 40:80] = 220
    small, large = tmp_path / "eight.tif", tmp_path / "sixteen.tif"
    Image.fromarray(pixels).save(small)
    Image.fromarray((pixels.astype(np.uint16) * 257).astype(dtype)).save(large)
    analyzer = AdaptiveSegmentationAnalyzer()
    first = analyzer.analyze([small], tmp_path / "first", ".")
    second = analyzer.analyze([large], tmp_path / "second", ".")
    assert first.image_results[0].object_count == second.image_results[0].object_count == 1
    assert first.metrics == second.metrics
    np.testing.assert_array_equal(read_image(small)[0], read_image(large)[0])


def test_image_pixel_limit_before_decode(tmp_path: Path):
    path = tmp_path / "field.png"
    Image.new("L", (100, 100)).save(path)
    with pytest.raises(ValueError, match="trop grande"):
        read_image(path, max_pixels=9999)


def test_multipage_tiff_is_not_silently_truncated(tmp_path: Path):
    path = tmp_path / "stack.tif"
    Image.new("L", (32, 32)).save(
        path, save_all=True, append_images=[Image.new("L", (32, 32), 255)]
    )
    with pytest.raises(ValueError, match="multipages"):
        read_image(path)


def test_8_bit_rgb_conversion_remains_identical(tmp_path: Path):
    path = tmp_path / "color.png"
    source = Image.new("RGB", (32, 32), (81, 32, 218))
    source.save(path)
    rgb, gray = read_image(path)
    np.testing.assert_array_equal(rgb, np.asarray(source))
    np.testing.assert_array_equal(gray, np.asarray(source.convert("L"), dtype=np.float32) / 255)
