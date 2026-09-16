import json
import shutil
import zipfile
from pathlib import Path

import pytest

from training.ooc_cnn.archive import create_artifact_archive
from training.ooc_cnn.manifests import sha256_file

SOURCE_BUNDLE_SHA256 = "b" * 64
SOURCE_COMMIT = "c" * 40


def _write_run_report(run: Path, *, run_id: str = "canonical-validation-run") -> None:
    (run / "validation-report.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "experiment_id": "fixture-experiment",
                "run_id": run_id,
                "mode": "validation",
                "config": {"path": "config.json", "sha256": "a" * 64},
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_artifact_archive_is_deterministic_and_self_describing(tmp_path: Path) -> None:
    run = tmp_path / "kaggle-validation-campaign-v2"
    (run / "onnx").mkdir(parents=True)
    (run / "best-checkpoint.pt").write_bytes(b"checkpoint")
    _write_run_report(run)
    (run / "onnx/model.onnx").write_bytes(b"onnx")
    (run / "artifact-manifest.json").write_text("stale\n", encoding="utf-8")

    first = create_artifact_archive(
        run_directory=run,
        output_path=tmp_path / "first.zip",
        source_bundle_sha256=SOURCE_BUNDLE_SHA256,
        source_commit=SOURCE_COMMIT,
        archive_root="organchip-cnn-validation-campaign-v2",
    )
    second = create_artifact_archive(
        run_directory=run,
        output_path=tmp_path / "second.zip",
        source_bundle_sha256=SOURCE_BUNDLE_SHA256,
        source_commit=SOURCE_COMMIT,
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
        assert manifest["schema_version"] == 2
        assert manifest["run_id"] == "canonical-validation-run"
        assert manifest["provenance"] == {
            "config": {"path": "config.json", "sha256": "a" * 64},
            "experiment_id": "fixture-experiment",
            "mode": "validation",
            "run_report": {
                "path": "validation-report.json",
                "sha256": sha256_file(run / "validation-report.json"),
            },
            "source_bundle_sha256": SOURCE_BUNDLE_SHA256,
            "source_commit": SOURCE_COMMIT,
        }
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
    _write_run_report(run)

    with pytest.raises(ValueError, match="outside the run directory"):
        create_artifact_archive(
            run_directory=run,
            output_path=run / "artifacts.zip",
            source_bundle_sha256=SOURCE_BUNDLE_SHA256,
            source_commit=SOURCE_COMMIT,
        )

    existing = tmp_path / "existing.zip"
    existing.write_bytes(b"do not overwrite")
    with pytest.raises(FileExistsError):
        create_artifact_archive(
            run_directory=run,
            output_path=existing,
            source_bundle_sha256=SOURCE_BUNDLE_SHA256,
            source_commit=SOURCE_COMMIT,
        )


def test_artifact_archive_rejects_symbolic_links(tmp_path: Path) -> None:
    run = tmp_path / "run"
    run.mkdir()
    _write_run_report(run)
    outside = tmp_path / "outside.txt"
    outside.write_text("outside\n", encoding="utf-8")
    (run / "linked.txt").symlink_to(outside)

    with pytest.raises(ValueError, match="symbolic link"):
        create_artifact_archive(
            run_directory=run,
            output_path=tmp_path / "artifacts.zip",
            source_bundle_sha256=SOURCE_BUNDLE_SHA256,
            source_commit=SOURCE_COMMIT,
        )


def test_artifact_identity_does_not_depend_on_extraction_directory(tmp_path: Path) -> None:
    first_run = tmp_path / "first-directory-name"
    first_run.mkdir()
    _write_run_report(first_run, run_id="stable-run-id")
    (first_run / "result.json").write_text('{"value": 1}\n', encoding="utf-8")
    second_run = tmp_path / "different-directory-name"
    shutil.copytree(first_run, second_run)

    first = create_artifact_archive(
        run_directory=first_run,
        output_path=tmp_path / "first.zip",
        source_bundle_sha256=SOURCE_BUNDLE_SHA256,
        source_commit=SOURCE_COMMIT,
    )
    second = create_artifact_archive(
        run_directory=second_run,
        output_path=tmp_path / "second.zip",
        source_bundle_sha256=SOURCE_BUNDLE_SHA256,
        source_commit=SOURCE_COMMIT,
    )

    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert first["sha256"] == second["sha256"]
