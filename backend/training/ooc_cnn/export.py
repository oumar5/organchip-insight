"""Export a frozen OoC MobileNetV3 checkpoint to ONNX and verify parity."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from training.ooc_cnn.configuration import ExperimentConfig
from training.ooc_cnn.manifests import (
    relative_project_path,
    sha256_file,
    validate_sha256,
)
from training.ooc_cnn.model import build_mobilenet_v3_small
from training.ooc_cnn.provenance import artifact_record, utc_now, write_json_atomic


def _load_selection_report(
    *,
    project_root: Path,
    config: ExperimentConfig,
    checkpoint_path: Path,
    checkpoint_sha256: str,
    report_path: Path,
    report_sha256: str,
) -> tuple[dict[str, Any], float]:
    relative_project_path(project_root, report_path, field="selection report")
    expected_report_sha256 = validate_sha256(
        report_sha256, "selection report sha256"
    )
    if sha256_file(report_path) != expected_report_sha256:
        raise ValueError("Selection report checksum mismatch")
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("Selection report is not valid JSON") from error
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("Selection report must use schema_version 1")
    mode = report.get("mode")
    if mode not in {"smoke", "validation"}:
        raise ValueError("Export requires a smoke or validation selection report")
    if report.get("experiment_id") != config.experiment_id:
        raise ValueError("Selection report experiment does not match the config")
    config_record = report.get("config")
    artifacts = report.get("artifacts")
    selection = report.get("selection")
    split = report.get("split")
    if not all(isinstance(value, dict) for value in (config_record, artifacts, selection, split)):
        raise ValueError("Selection report provenance is incomplete")
    if config_record.get("path") != relative_project_path(
        project_root, config.path, field="CNN config"
    ) or config_record.get("sha256") != config.sha256:
        raise ValueError("Selection report config provenance does not match")
    checkpoint_record = artifacts.get("checkpoint")
    if not isinstance(checkpoint_record, dict):
        raise ValueError("Selection report checkpoint provenance is missing")
    if checkpoint_record.get("path") != relative_project_path(
        project_root, checkpoint_path, field="CNN checkpoint"
    ) or checkpoint_record.get("sha256") != checkpoint_sha256:
        raise ValueError("Selection report checkpoint provenance does not match")
    if split.get("test_manifest_opened") is not False:
        raise ValueError("Selection report must prove that the test manifest stayed closed")
    if mode == "validation" and report.get("benchmark_eligible") is not True:
        raise ValueError("Validation selection report is not benchmark eligible")
    if mode == "smoke" and report.get("benchmark_eligible") is not False:
        raise ValueError("Smoke selection report must not be benchmark eligible")
    threshold = selection.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, int | float):
        raise ValueError("Selection report threshold is invalid")
    threshold = float(threshold)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Selection report threshold must be between zero and one")
    if selection.get("threshold_selected_on") != "validation":
        raise ValueError("Export threshold must have been selected on validation")
    return report, threshold


def export_checkpoint(
    *,
    project_root: Path,
    config: ExperimentConfig,
    checkpoint_path: Path,
    checkpoint_sha256: str,
    selection_report_path: Path,
    selection_report_sha256: str,
    output_directory: Path,
    runtime_snapshot: dict[str, Any],
) -> dict[str, Any]:
    root = project_root.resolve()
    relative_project_path(root, checkpoint_path, field="ONNX checkpoint")
    relative_project_path(root, output_directory, field="ONNX output directory")
    checkpoint_sha256 = validate_sha256(checkpoint_sha256, "checkpoint sha256")
    if sha256_file(checkpoint_path) != checkpoint_sha256:
        raise ValueError("Checkpoint checksum mismatch before ONNX export")
    selection_report, threshold = _load_selection_report(
        project_root=root,
        config=config,
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=checkpoint_sha256,
        report_path=selection_report_path,
        report_sha256=selection_report_sha256,
    )
    output_directory.mkdir(parents=True, exist_ok=True)
    onnx_path = output_directory / "model.onnx"
    preprocessing_path = output_directory / "preprocessing.json"
    labels_path = output_directory / "labels.json"
    report_path = output_directory / "export-report.json"
    if any(path.exists() for path in (onnx_path, preprocessing_path, labels_path, report_path)):
        raise ValueError("ONNX output directory already contains export artifacts")

    try:
        import onnx
        import onnxruntime
        import torch
    except (ImportError, RuntimeError) as error:
        raise RuntimeError("PyTorch, ONNX, and ONNX Runtime are required for export") from error

    checkpoint_payload = torch.load(
        checkpoint_path, map_location="cpu", weights_only=True
    )
    if not isinstance(checkpoint_payload, Mapping):
        raise ValueError("Export checkpoint must contain provenance metadata")
    if (
        checkpoint_payload.get("schema_version") != 1
        or checkpoint_payload.get("experiment_id") != config.experiment_id
        or checkpoint_payload.get("architecture") != "mobilenet_v3_small"
        or checkpoint_payload.get("config_sha256") != config.sha256
        or checkpoint_payload.get("train_validation_manifest_sha256")
        != config.train_validation_manifest_sha256
        or not isinstance(checkpoint_payload.get("state_dict"), Mapping)
    ):
        raise ValueError("Export checkpoint provenance does not match the experiment")

    torch.manual_seed(int(config.raw["training"]["seed"]))
    model = build_mobilenet_v3_small(
        weights=checkpoint_path,
        expected_sha256=checkpoint_sha256,
        weights_role="checkpoint",
    ).cpu()
    model.eval()
    image_size = int(config.raw["preprocessing"]["input_size"])
    sample = torch.randn(2, 3, image_size, image_size, dtype=torch.float32)
    with torch.inference_mode():
        expected = model(sample).detach().cpu().numpy()
    export_config = config.raw["export"]
    dynamic_axes = (
        {"images": {0: "batch"}, "logits": {0: "batch"}}
        if export_config["dynamic_batch"]
        else None
    )
    torch.onnx.export(
        model,
        sample,
        onnx_path,
        input_names=["images"],
        output_names=["logits"],
        dynamic_axes=dynamic_axes,
        opset_version=int(export_config["onnx_opset"]),
        do_constant_folding=True,
        dynamo=False,
    )
    graph = onnx.load(onnx_path)
    onnx.checker.check_model(graph)
    session = onnxruntime.InferenceSession(
        str(onnx_path), providers=["CPUExecutionProvider"]
    )
    parity_errors: list[float] = []
    parity_batch_sizes = (1, 2, 3)
    for batch_size in parity_batch_sizes:
        parity_input = (
            sample
            if batch_size == int(sample.shape[0])
            else torch.randn(
                batch_size, 3, image_size, image_size, dtype=torch.float32
            )
        )
        with torch.inference_mode():
            expected_logits = (
                expected
                if parity_input is sample
                else model(parity_input).detach().cpu().numpy()
            )
        actual_logits = session.run(
            ["logits"], {"images": parity_input.numpy()}
        )[0]
        if not np.isfinite(actual_logits).all():
            raise RuntimeError("ONNX parity failed: non-finite output")
        parity_errors.append(
            float(np.max(np.abs(expected_logits - actual_logits)))
        )
    maximum_absolute_error = max(parity_errors)
    tolerance = float(export_config["parity_absolute_tolerance"])
    if maximum_absolute_error > tolerance:
        raise RuntimeError(
            f"ONNX parity failed: max abs error {maximum_absolute_error} > {tolerance}"
        )

    write_json_atomic(
        preprocessing_path,
        {
            "schema_version": 1,
            "input_name": "images",
            "layout": "NCHW",
            "dtype": "float32",
            "decision_threshold": threshold,
            **config.raw["preprocessing"],
        },
    )
    write_json_atomic(
        labels_path,
        {
            "schema_version": 1,
            "output_name": "logits",
            "class_to_index": {"bad": 0, "good": 1},
            "positive_class": "good",
            "decision_threshold": threshold,
            "threshold_selected_on": "validation",
        },
    )
    report = {
        "schema_version": 1,
        "experiment_id": config.experiment_id,
        "generated_at_utc": utc_now(),
        "config_sha256": config.sha256,
        "checkpoint": artifact_record(root, checkpoint_path),
        "selection_report": artifact_record(root, selection_report_path),
        "benchmark_eligible_source": bool(selection_report["benchmark_eligible"]),
        "selected_threshold": threshold,
        "runtime": runtime_snapshot,
        "export": {
            "format": "ONNX",
            "opset": int(export_config["onnx_opset"]),
            "dynamic_batch": bool(export_config["dynamic_batch"]),
            "fixed_spatial_size": image_size,
            "parity_batch_sizes": list(parity_batch_sizes),
            "parity_samples": sum(parity_batch_sizes),
            "parity_maximum_absolute_error": maximum_absolute_error,
            "parity_absolute_tolerance": tolerance,
            "parity_passed": True,
        },
        "artifacts": {
            "onnx": artifact_record(root, onnx_path),
            "preprocessing": artifact_record(root, preprocessing_path),
            "labels": artifact_record(root, labels_path),
        },
    }
    write_json_atomic(report_path, report)
    report["report"] = {
        "path": relative_project_path(root, report_path, field="export report"),
        "sha256": sha256_file(report_path),
    }
    return report
