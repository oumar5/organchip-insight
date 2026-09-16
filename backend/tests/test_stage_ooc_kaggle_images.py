import csv
import hashlib
import importlib.util
import json
import zipfile

import pytest

ROOT = __file__.rsplit("/backend/tests/", 1)[0]
SPEC = importlib.util.spec_from_file_location(
    "stage_ooc_kaggle_images", f"{ROOT}/backend/scripts/stage_ooc_kaggle_images.py"
)
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)


def test_stages_verified_deterministic_bundle(tmp_path, monkeypatch):
    root = tmp_path / "project"
    image = root / "data/raw/ooc/example.png"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"example microscopy bytes")
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    manifest = root / "split.csv"
    with manifest.open("w", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=["path", "grouped_split", "sha256"])
        writer.writeheader()
        writer.writerow(
            {
                "path": "data/raw/ooc/example.png",
                "grouped_split": "test",
                "sha256": digest,
            }
        )
    monkeypatch.setattr(stage, "ROOT", root)
    first = stage.write_bundle(
        manifest=manifest, split_role="frozen-test", output=tmp_path / "first"
    )
    second = stage.write_bundle(
        manifest=manifest, split_role="frozen-test", output=tmp_path / "second"
    )
    assert first == second
    assert first["privacy"] == "private"
    assert first["archive"]["member_count"] == 1
    assert json.loads((tmp_path / "first/dataset-metadata.json").read_text())["id"].endswith(
        "frozen-test"
    )
    with zipfile.ZipFile(tmp_path / "first/images.zip") as archive:
        assert archive.namelist() == ["data/raw/ooc/example.png"]
        assert archive.read(archive.namelist()[0]) == image.read_bytes()


def test_rejects_wrong_role_and_hash(tmp_path, monkeypatch):
    monkeypatch.setattr(stage, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="split_role"):
        stage.write_bundle(manifest=tmp_path / "missing", split_role="all", output=tmp_path / "out")
    manifest = tmp_path / "manifest.csv"
    manifest.write_text("path,grouped_split,sha256\nmissing.png,test," + "0" * 64 + "\n")
    with pytest.raises(ValueError, match="Missing"):
        stage.write_bundle(manifest=manifest, split_role="frozen-test", output=tmp_path / "out")
