from pathlib import Path

import pytest
from PIL import Image

from evaluation.build_iorganoassay_validation_manifest import build_manifest


def _write_fixture(root: Path, *, omit: str | None = None) -> None:
    for condition in ("Ctrl", "DSS"):
        condition_dir = root / condition
        condition_dir.mkdir(parents=True)
        for index in range(1, 15):
            sample_id = f"{condition}_{index:02d}"
            for role in ("BF", "GT", "Seg"):
                filename = f"{sample_id}_{role}.jpg"
                if filename == omit:
                    continue
                size = (12, 10) if role == "BF" else (8, 6)
                Image.new("RGB", size, "white").save(condition_dir / filename)


def test_manifest_locks_all_validation_triples(tmp_path: Path, monkeypatch) -> None:
    _write_fixture(tmp_path)
    monkeypatch.setattr(
        "evaluation.build_iorganoassay_validation_manifest.PROJECT_ROOT", tmp_path
    )

    manifest = build_manifest(tmp_path)

    assert manifest["sample_count"] == 28
    assert manifest["conditions"] == {"Ctrl": 14, "DSS": 14}
    assert len(manifest["samples"]) == 28
    assert all(len(sample["files"]) == 3 for sample in manifest["samples"])


def test_manifest_rejects_an_incomplete_triple(tmp_path: Path, monkeypatch) -> None:
    _write_fixture(tmp_path, omit="Ctrl_07_GT.jpg")
    monkeypatch.setattr(
        "evaluation.build_iorganoassay_validation_manifest.PROJECT_ROOT", tmp_path
    )

    with pytest.raises(ValueError, match="Missing files for Ctrl_07"):
        build_manifest(tmp_path)
