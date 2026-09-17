import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image

from app.ml.pipeline import AdaptiveSegmentationAnalyzer
from inference import resolve_input_images


def _image(path: Path, value: int = 120) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("L", (32, 32), value).save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_manifest_resolves_and_verifies_images(tmp_path: Path) -> None:
    digest = _image(tmp_path / "images/field.png")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "path_root": ".",
                "images": [{"path": "images/field.png", "sha256": digest}],
            }
        ),
        encoding="utf-8",
    )

    assert resolve_input_images([], [], manifest, recursive=False) == [
        (tmp_path / "images/field.png").resolve()
    ]


def test_manifest_rejects_hash_mismatch(tmp_path: Path) -> None:
    _image(tmp_path / "field.png")
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "images": [{"path": "field.png", "sha256": "0" * 64}],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        resolve_input_images([], [], manifest, recursive=False)


def test_directory_discovery_and_symlink_rejection(tmp_path: Path) -> None:
    image = tmp_path / "images/field.png"
    _image(image)
    assert resolve_input_images([], [image.parent], None, recursive=False) == [
        image.resolve()
    ]

    linked = tmp_path / "linked.png"
    try:
        linked.symlink_to(image)
    except OSError:
        pytest.skip("Symbolic links are unavailable")
    with pytest.raises(ValueError, match="Symbolic links"):
        resolve_input_images([linked], [], None, recursive=False)


def test_same_stem_overlays_do_not_collide(tmp_path: Path) -> None:
    first = tmp_path / "first/field.png"
    second = tmp_path / "second/field.tif"
    _image(first, 80)
    _image(second, 180)
    output = AdaptiveSegmentationAnalyzer().analyze(
        [first, second], tmp_path / "artifacts", "."
    )
    names = [artifact.filename for artifact in output.artifacts]
    assert len(names) == len(set(names)) == 2
    assert all((tmp_path / "artifacts" / name).is_file() for name in names)
