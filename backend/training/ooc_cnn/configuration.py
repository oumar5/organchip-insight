"""Validation for the versioned OoC CNN experiment configuration."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from training.ooc_cnn.manifests import (
    relative_project_path,
    resolve_project_path,
    sha256_file,
    validate_sha256,
)


@dataclass(frozen=True)
class ExperimentConfig:
    path: Path
    sha256: str
    raw: dict[str, Any]
    experiment_id: str
    split_lock_path: Path
    split_lock_sha256: str
    train_validation_manifest_path: Path
    train_validation_manifest_sha256: str
    runs_directory: Path
    generated_reports_directory: Path
    test_receipts_directory: Path


def _object(parent: dict[str, Any], name: str) -> dict[str, Any]:
    value = parent.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"CNN config {name} must be an object")
    return value


def _positive_integer(parent: dict[str, Any], name: str) -> int:
    value = parent.get(name)
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"CNN config {name} must be a positive integer")
    return value


def _positive_number(parent: dict[str, Any], name: str) -> float:
    value = parent.get(name)
    if isinstance(value, bool) or not isinstance(value, int | float) or value <= 0:
        raise ValueError(f"CNN config {name} must be a positive number")
    return float(value)


def _project_path(project_root: Path, parent: dict[str, Any], name: str) -> Path:
    value = parent.get(name)
    if not isinstance(value, str):
        raise ValueError(f"CNN config {name} must be a path string")
    return resolve_project_path(project_root, value, field=f"CNN config {name}")


def _validate_numeric_vector(value: object, name: str) -> tuple[float, float, float]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(isinstance(item, bool) or not isinstance(item, int | float) for item in value)
    ):
        raise ValueError(f"CNN config {name} must contain three numbers")
    return tuple(float(item) for item in value)  # type: ignore[return-value]


def load_experiment_config(path: Path, *, project_root: Path) -> ExperimentConfig:
    root = project_root.resolve()
    config_path = path.resolve()
    relative_project_path(root, config_path, field="CNN config path")
    try:
        value = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("CNN config is not valid JSON") from error
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("CNN config must use schema_version 1")
    experiment_id = value.get("experiment_id")
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("CNN config experiment_id is invalid")

    split = _object(value, "split")
    provenance = _object(value, "provenance")
    model = _object(value, "model")
    preprocessing = _object(value, "preprocessing")
    training = _object(value, "training")
    smoke = _object(value, "smoke")
    evaluation = _object(value, "evaluation")
    export = _object(value, "export")
    outputs = _object(value, "outputs")

    dataset = _object(value, "dataset")
    if dataset.get("target") != "expert good/bad image-quality label":
        raise ValueError("CNN dataset target must remain the expert image-quality label")

    if model.get("architecture") != "mobilenet_v3_small" or model.get("num_classes") != 2:
        raise ValueError("CNN config supports only binary MobileNetV3 Small")
    if model.get("label_mapping") != {"0": "bad", "1": "good"}:
        raise ValueError("CNN config label mapping must be bad=0 and good=1")
    if model.get("implicit_weight_downloads") is not False:
        raise ValueError("CNN config must forbid implicit weight downloads")

    input_size = _positive_integer(preprocessing, "input_size")
    if input_size not in {224, 448}:
        raise ValueError("CNN preprocessing input_size must be 224 or 448")
    if preprocessing.get("force_rgb") is not True:
        raise ValueError("CNN preprocessing must produce three-channel model inputs")
    if preprocessing.get("color_mode") not in {"rgb", "grayscale_rgb"}:
        raise ValueError("CNN preprocessing color_mode must be rgb or grayscale_rgb")
    if preprocessing.get("resize") != "preserve aspect ratio and pad to square":
        raise ValueError("CNN preprocessing must preserve aspect ratio and pad")
    if preprocessing.get("interpolation") != "bilinear":
        raise ValueError("CNN preprocessing must use bilinear interpolation")
    if preprocessing.get("pad_value") != 0:
        raise ValueError("CNN preprocessing must use black padding")
    if preprocessing.get("train_augmentations") != [
        "horizontal_flip",
        "vertical_flip",
    ]:
        raise ValueError("CNN training augmentations do not match the implementation")
    mean = _validate_numeric_vector(preprocessing.get("mean"), "mean")
    std = _validate_numeric_vector(preprocessing.get("std"), "std")
    if any(item <= 0 for item in std):
        raise ValueError("CNN config standard deviations must be positive")
    if mean != (0.485, 0.456, 0.406) or std != (0.229, 0.224, 0.225):
        raise ValueError("CNN normalization must match the pinned ImageNet constants")

    for name in ("seed", "epochs", "batch_size", "workers", "early_stopping_patience"):
        _positive_integer(training, name)
    for name in ("learning_rate", "weight_decay"):
        _positive_number(training, name)
    if training.get("amp_on_cuda") is not True:
        raise ValueError("CNN training must enable AMP on CUDA")
    if training.get("deterministic_algorithms") is not True:
        raise ValueError("CNN training must request deterministic algorithms")
    for name in (
        "epochs",
        "batch_size",
        "max_train_images",
        "max_validation_images",
    ):
        _positive_integer(smoke, name)
    workers = smoke.get("workers")
    if isinstance(workers, bool) or not isinstance(workers, int) or workers < 0:
        raise ValueError("CNN smoke workers must be a non-negative integer")
    if smoke.get("benchmark_eligible") is not False:
        raise ValueError("CNN smoke runs must never be benchmark eligible")
    for name in ("threshold_grid_steps", "ece_bins", "bootstrap_iterations"):
        _positive_integer(evaluation, name)
    grid_start = _positive_number(evaluation, "threshold_grid_start")
    grid_stop = _positive_number(evaluation, "threshold_grid_stop")
    if not 0.0 < grid_start < grid_stop < 1.0:
        raise ValueError("CNN threshold grid must be strictly inside zero and one")
    if int(evaluation["threshold_grid_steps"]) < 2:
        raise ValueError("CNN threshold grid requires at least two steps")
    if _positive_integer(export, "fixed_spatial_size") != input_size:
        raise ValueError("CNN export and preprocessing spatial sizes must match")
    if _positive_integer(export, "onnx_opset") < 18:
        raise ValueError("CNN ONNX export requires opset 18 or newer")
    if export.get("dynamic_batch") is not True:
        raise ValueError("CNN ONNX export must support a dynamic batch axis")
    _positive_number(export, "parity_absolute_tolerance")

    lock_sha = validate_sha256(split.get("lock_sha256"), "CNN split lock_sha256")
    train_sha = validate_sha256(
        split.get("train_validation_sha256"), "CNN train/validation sha256"
    )
    inventory_sha = validate_sha256(
        provenance.get("inventory_sha256"), "CNN inventory sha256"
    )
    contract_sha = validate_sha256(
        provenance.get("runtime_contract_sha256"), "CNN runtime contract sha256"
    )
    inventory_path = _project_path(root, provenance, "inventory_path")
    contract_path = _project_path(root, provenance, "runtime_contract_path")
    for artifact_path, expected, label in (
        (inventory_path, inventory_sha, "inventory"),
        (contract_path, contract_sha, "runtime contract"),
    ):
        if not artifact_path.is_file() or sha256_file(artifact_path) != expected:
            raise ValueError(f"CNN {label} checksum mismatch")

    split_lock_path = _project_path(root, split, "lock_path")
    train_validation_manifest_path = _project_path(
        root, split, "train_validation_manifest"
    )
    for artifact_path, expected, label in (
        (split_lock_path, lock_sha, "split lock"),
        (train_validation_manifest_path, train_sha, "train/validation manifest"),
    ):
        if not artifact_path.is_file() or sha256_file(artifact_path) != expected:
            raise ValueError(f"CNN {label} checksum mismatch")
    return ExperimentConfig(
        path=config_path,
        sha256=sha256_file(config_path),
        raw=value,
        experiment_id=experiment_id.strip(),
        split_lock_path=split_lock_path,
        split_lock_sha256=lock_sha,
        train_validation_manifest_path=train_validation_manifest_path,
        train_validation_manifest_sha256=train_sha,
        runs_directory=_project_path(root, outputs, "runs_directory"),
        generated_reports_directory=_project_path(
            root, outputs, "generated_reports_directory"
        ),
        test_receipts_directory=_project_path(root, outputs, "test_receipts_directory"),
    )
