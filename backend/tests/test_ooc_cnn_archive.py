import json
import zipfile
from pathlib import Path

import pytest

from training.ooc_cnn.archive import create_artifact_archive
from training.ooc_cnn.manifests import sha256_file


def test_artifact_archive_is_deterministic_and_self_describing(tmp_path: Path) -> None:
    run = tmp_path / "kaggle-validation-campaign-v2"
    (run / "onnx").mkdir(parents=True)
    (run / "best-checkpoint.pt").write_bytes(b"checkpoint")
    (run / "validation-report.json").write_text("{}\n", encoding="utf-8")
    (run / "onnx/model.onnx").write_bytes(b"onnx")
    (run / "artifact-manifest.json").write_text("stale\n", encoding="utf-8")

    first = create_artifact_archive(
        run_directory=run,
        output_path=tmp_path / "first.zip",
        archive_root="organchip-cnn-validation-campaign-v2",
    )
    second = create_artifact_archive(
        run_directory=run,
        output_path=tmp_path / "second.zip",
        archive_root="organchip-cnn-validation-campaign-v2",
    )

    assert first["sha256"] == second["sha256"]
    assert first["file_count"] == 3
    with zipfile.ZipFile(tmp_path / "first.zip") as archive:
        assert archive.testzip() is None
        names = archive.namelist()
        assert names[0] == (
            "organchip-cnn-validation-campaign-v2/artifact-manifest.json"
        )
        assert names.count(names[0]) == 1
        manifest = json.loads(archive.read(names[0]))
        assert manifest["run_id"] == run.name
        assert [record["path"] for record in manifest["files"]] == [
            "best-checkpoint.pt",
            "onnx/model.onnx",
            "validation-report.json",
        ]
        assert manifest["files"][0]["sha256"] == sha256_file(
            run / "best-checkpoint.pt"
        )


def test_artifact_archive_rejects_unsafe_or_ambiguous_destinations(
    tmp_path: Path,
) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "report.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the run directory"):
        create_artifact_archive(
            run_directory=run,
            output_path=run / "artifacts.zip",
        )

    existing = tmp_path / "existing.zip"
    existing.write_bytes(b"do not overwrite")
    with pytest.raises(FileExistsError):
        create_artifact_archive(run_directory=run, output_path=existing)


def test_artifact_archive_rejects_symbolic_links(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (run / "linked.txt").symlink_to(outside)

    with pytest.raises(ValueError, match="symbolic link"):
        create_artifact_archive(
            run_directory=run,
            output_path=tmp_path / "artifacts.zip",
        )
