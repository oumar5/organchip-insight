import importlib.util
import json
import zipfile

import pytest

ROOT = __file__.rsplit("/backend/tests/", 1)[0]
SPEC = importlib.util.spec_from_file_location(
    "stage_ooc_kaggle_source", f"{ROOT}/backend/scripts/stage_ooc_kaggle_source.py"
)
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)


def _source_fixture(root):
    paths = (
        "backend/training/__init__.py",
        "backend/training/ooc_cnn/__init__.py",
        "backend/training/ooc_cnn/cli.py",
        "backend/experiments/ooc-cnn/kaggle-runtime-contract.json",
        "backend/training/configs/ooc-cnn-mobilenet-v3-small-campaign-v2.json",
        "data/splits/ooc-campaign-v2-lock.json",
        "data/splits/ooc-campaign-v2-train-validation.csv",
        "reports/ooc-image-inventory-2026-09-16.csv",
    )
    for relative in paths:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"fixture: {relative}\n", encoding="utf-8")
    forbidden = root / "data/splits/ooc-campaign-v2-test.csv"
    forbidden.write_text("frozen test labels\n", encoding="utf-8")


def test_source_bundle_is_allowlisted_and_deterministic(tmp_path):
    root = tmp_path / "project"
    _source_fixture(root)
    first = stage.write_bundle(output=tmp_path / "first", root=root)
    second = stage.write_bundle(output=tmp_path / "second", root=root)

    assert first["source_tree_sha256"] == second["source_tree_sha256"]
    assert first["archive"]["sha256"] == second["archive"]["sha256"]
    assert first["privacy"] == "private"
    assert json.loads((tmp_path / "first/upload-manifest.json").read_text()) == first
    with zipfile.ZipFile(tmp_path / "first/organchip-insight-source-campaign-v2.zip") as archive:
        names = archive.namelist()
        assert "organchip-insight/backend/training/ooc_cnn/cli.py" in names
        assert not any("ooc-campaign-v2-test.csv" in name for name in names)
        assert not any("data/raw" in name for name in names)
        manifest = json.loads(archive.read("source-bundle-manifest.json"))
        assert manifest["source_tree_sha256"] == first["source_tree_sha256"]


def test_source_bundle_refuses_overwrite_and_missing_inputs(tmp_path):
    root = tmp_path / "project"
    _source_fixture(root)
    output = tmp_path / "bundle"
    stage.write_bundle(output=output, root=root)
    with pytest.raises(FileExistsError, match="overwrite"):
        stage.write_bundle(output=output, root=root)

    (root / "data/splits/ooc-campaign-v2-lock.json").unlink()
    with pytest.raises(ValueError, match="Missing"):
        stage.write_bundle(output=tmp_path / "missing", root=root)
