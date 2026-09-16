"""Freeze a validation-selected CNN before any final test evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from training.ooc_cnn.manifests import (
    load_split_lock,
    relative_project_path,
    sha256_file,
)
from training.ooc_cnn.provenance import source_hashes, utc_now, write_json_atomic


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _artifact(
    project_root: Path,
    path: Path,
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    relative = relative_project_path(project_root, path, field="frozen artifact")
    if not path.is_file():
        raise ValueError(f"Frozen artifact is missing: {relative}")
    actual_sha256 = sha256_file(path)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise ValueError(f"Frozen artifact checksum mismatch: {relative}")
    return {"path": relative, "sha256": actual_sha256}


def create_frozen_manifest(
    *,
    project_root: Path,
    config_path: Path,
    validation_report_path: Path,
    checkpoint_path: Path,
    split_lock_path: Path,
    split_lock_sha256: str,
    output_path: Path,
    source_paths: list[Path],
) -> dict[str, Any]:
    root = project_root.resolve()
    relative_project_path(root, output_path, field="frozen manifest output")
    if output_path.exists():
        raise ValueError("Frozen manifest output already exists")
    if not source_paths:
        raise ValueError("At least one frozen source file is required")
    report = _load_json(validation_report_path, "Validation report")
    if report.get("schema_version") != 1 or report.get("mode") != "validation":
        raise ValueError("Only a schema-version 1 validation report can be frozen")
    if report.get("benchmark_eligible") is not True:
        raise ValueError("Validation report is not benchmark eligible")
    report_split = report.get("split")
    if not isinstance(report_split, dict):
        raise ValueError("Validation report split provenance is incomplete")
    if report_split.get("test_manifest_opened") is not False:
        raise ValueError("Validation report must prove that the test manifest stayed closed")
    training = report.get("training")
    initialization = report.get("initialization")
    if not isinstance(training, dict) or training.get("device") != "cuda":
        raise ValueError("Validation report must come from the required CUDA runtime")
    if (
        not isinstance(initialization, dict)
        or initialization.get("external_weights") is not True
    ):
        raise ValueError("Validation report must record explicit pretrained weights")
    experiment_id = report.get("experiment_id")
    selection = report.get("selection")
    if not isinstance(experiment_id, str) or not experiment_id:
        raise ValueError("Validation report experiment_id is invalid")
    if not isinstance(selection, dict):
        raise ValueError("Validation report selection is invalid")
    if selection.get("threshold_selected_on") != "validation":
        raise ValueError("Validation report threshold must be selected on validation")
    if selection.get("checkpoint_metric") != "validation macro_f1 at threshold 0.5":
        raise ValueError("Validation report checkpoint metric is invalid")
    best_epoch = selection.get("best_epoch")
    if isinstance(best_epoch, bool) or not isinstance(best_epoch, int) or best_epoch <= 0:
        raise ValueError("Validation report best epoch is invalid")
    threshold = selection.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, int | float):
        raise ValueError("Validation report threshold is invalid")
    threshold = float(threshold)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Validation report threshold must be between zero and one")

    report_artifacts = report.get("artifacts")
    config_record = report.get("config")
    if not isinstance(report_artifacts, dict) or not isinstance(config_record, dict):
        raise ValueError("Validation report artifact provenance is incomplete")
    checkpoint_record = report_artifacts.get("checkpoint")
    if not isinstance(checkpoint_record, dict):
        raise ValueError("Validation report checkpoint provenance is incomplete")
    expected_checkpoint_sha256 = checkpoint_record.get("sha256")
    expected_config_sha256 = config_record.get("sha256")
    if not isinstance(expected_checkpoint_sha256, str) or not isinstance(
        expected_config_sha256, str
    ):
        raise ValueError("Validation report artifact hashes are incomplete")

    split_lock = load_split_lock(
        split_lock_path,
        project_root=root,
        expected_sha256=split_lock_sha256,
    )
    config = _load_json(config_path, "CNN config")
    if config.get("experiment_id") != experiment_id:
        raise ValueError("Validation report experiment does not match the CNN config")
    expected_config_path = relative_project_path(root, config_path, field="CNN config")
    if config_record.get("path") != expected_config_path:
        raise ValueError("Validation report config path does not match the CNN config")
    if report_split.get("lock_sha256") != split_lock.sha256:
        raise ValueError("Validation report split lock checksum does not match")
    if (
        report_split.get("train_validation_manifest_sha256")
        != split_lock.train_validation.sha256
    ):
        raise ValueError("Validation report train/validation checksum does not match")
    checkpoint_relative = relative_project_path(
        root, checkpoint_path, field="validation checkpoint"
    )
    if checkpoint_record.get("path") != checkpoint_relative:
        raise ValueError("Validation report checkpoint path does not match")
    frozen_sources = source_hashes(root, source_paths)
    if report.get("source_files") != frozen_sources:
        raise ValueError("Validation report source hashes do not match the active runtime")
    protected_paths = {
        config_path.resolve(),
        validation_report_path.resolve(),
        checkpoint_path.resolve(),
        split_lock_path.resolve(),
        split_lock.train_validation.path,
        split_lock.test.path,
        *(path.resolve() for path in source_paths),
    }
    if output_path.resolve() in protected_paths:
        raise ValueError("Frozen manifest output must be distinct from its inputs")
    artifacts = {
        "config": _artifact(root, config_path, expected_sha256=expected_config_sha256),
        "validation_report": _artifact(root, validation_report_path),
        "checkpoint": _artifact(
            root,
            checkpoint_path,
            expected_sha256=expected_checkpoint_sha256,
        ),
        "train_validation_manifest": {
            "path": split_lock.train_validation.relative_path,
            "sha256": split_lock.train_validation.sha256,
        },
        "test_manifest": {
            "path": split_lock.test.relative_path,
            "sha256": split_lock.test.sha256,
        },
        "split_lock": _artifact(root, split_lock_path, expected_sha256=split_lock_sha256),
    }
    frozen = {
        "schema_version": 1,
        "experiment_id": experiment_id,
        "created_at_utc": utc_now(),
        "policy": {
            "selection_split": "validation",
            "test_used_for_selection": False,
            "test_manifest_opened_while_freezing": False,
            "workspace_receipt_required_before_test_open": True,
            "workspace_receipt_blocks_repeat_access": True,
            "global_single_access_enforced": False,
        },
        "selection": {
            "checkpoint_metric": selection.get("checkpoint_metric"),
            "best_epoch": best_epoch,
            "threshold": threshold,
            "threshold_selected_on": "validation",
        },
        "artifacts": artifacts,
        "source_files": frozen_sources,
    }
    write_json_atomic(output_path, frozen, overwrite=False)
    return frozen
