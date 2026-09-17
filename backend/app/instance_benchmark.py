from __future__ import annotations

import csv
import hashlib
import json
import platform
import resource
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy.optimize import linear_sum_assignment

from app.benchmark import _load_engine
from app.ml.image_io import read_image


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_mask_tree(mask_dir: Path, project_root: Path) -> str:
    digest = hashlib.sha256()
    mask_paths = sorted(mask_dir.glob("*.png"))
    if not mask_paths:
        raise FileNotFoundError(f"No instance masks found in {mask_dir}")
    for mask_path in mask_paths:
        digest.update(str(mask_path.relative_to(project_root)).encode("utf-8"))
        digest.update(b"\0")
        digest.update(_sha256_file(mask_path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0


def _relabel(labels: np.ndarray) -> tuple[np.ndarray, int]:
    if labels.ndim != 2:
        raise ValueError(f"Instance labels must be 2D, got shape {labels.shape}")
    unique = np.unique(labels)
    foreground = unique[unique != 0]
    if not len(foreground):
        return np.zeros(labels.shape, dtype=np.int32), 0
    indices = np.searchsorted(foreground, labels)
    relabeled = np.where(labels == 0, 0, indices + 1).astype(np.int32)
    return relabeled, int(len(foreground))


def instance_iou_matrix(prediction: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """Return pairwise IoU for non-zero predicted and truth instance labels."""
    prediction, predicted_count = _relabel(prediction)
    truth, truth_count = _relabel(truth)
    if prediction.shape != truth.shape:
        raise ValueError(
            f"Label shape mismatch: prediction={prediction.shape}, truth={truth.shape}"
        )
    if not predicted_count or not truth_count:
        return np.zeros((truth_count, predicted_count), dtype=np.float64)

    encoded = truth.ravel().astype(np.int64) * (predicted_count + 1)
    encoded += prediction.ravel().astype(np.int64)
    intersections = np.bincount(
        encoded,
        minlength=(truth_count + 1) * (predicted_count + 1),
    ).reshape(truth_count + 1, predicted_count + 1)[1:, 1:]
    truth_areas = np.bincount(truth.ravel(), minlength=truth_count + 1)[1:, None]
    predicted_areas = np.bincount(
        prediction.ravel(), minlength=predicted_count + 1
    )[None, 1:]
    unions = truth_areas + predicted_areas - intersections
    return np.divide(
        intersections,
        unions,
        out=np.zeros(intersections.shape, dtype=np.float64),
        where=unions > 0,
    )


def object_metrics(
    prediction: np.ndarray,
    truth: np.ndarray,
    *,
    iou_threshold: float,
) -> dict[str, float | int]:
    if not 0 < iou_threshold <= 1:
        raise ValueError("IoU threshold must be in (0, 1]")
    ious = instance_iou_matrix(prediction, truth)
    truth_count, predicted_count = ious.shape
    if truth_count and predicted_count:
        valid = ious >= iou_threshold
        cardinality_bonus = min(truth_count, predicted_count) + 1
        objective = valid.astype(np.float64) * cardinality_bonus + ious
        truth_indices, predicted_indices = linear_sum_assignment(-objective)
        matched_ious = ious[truth_indices, predicted_indices]
        matched_ious = matched_ious[matched_ious >= iou_threshold]
    else:
        matched_ious = np.asarray([], dtype=np.float64)

    true_positive = int(len(matched_ious))
    false_positive = predicted_count - true_positive
    false_negative = truth_count - true_positive
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": _ratio(
            2 * true_positive,
            2 * true_positive + false_positive + false_negative,
        ),
        "mean_matched_iou": float(matched_ious.mean()) if len(matched_ious) else 0.0,
    }


def _foreground_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float]:
    predicted = prediction != 0
    expected = truth != 0
    intersection = int(np.count_nonzero(predicted & expected))
    predicted_pixels = int(np.count_nonzero(predicted))
    truth_pixels = int(np.count_nonzero(expected))
    union = predicted_pixels + truth_pixels - intersection
    return {
        "pixel_precision": _ratio(intersection, predicted_pixels),
        "pixel_recall": _ratio(intersection, truth_pixels),
        "pixel_f1": _ratio(intersection * 2, predicted_pixels + truth_pixels),
        "pixel_iou": _ratio(intersection, union),
    }


def load_instance_truth(mask_dir: Path, expected_shape: tuple[int, int]) -> np.ndarray:
    mask_paths = sorted(mask_dir.glob("*.png"))
    if not mask_paths:
        raise FileNotFoundError(f"No instance masks found in {mask_dir}")
    labels = np.zeros(expected_shape, dtype=np.int32)
    for label, mask_path in enumerate(mask_paths, start=1):
        with Image.open(mask_path) as source:
            mask = np.asarray(source.convert("L")) > 0
        if mask.shape != expected_shape:
            raise ValueError(
                f"Mask shape mismatch for {mask_path}: {mask.shape} != {expected_shape}"
            )
        if np.any((labels != 0) & mask):
            raise ValueError(f"Overlapping BBBC038 instance masks in {mask_dir}")
        labels[mask] = label
    return labels


def _bootstrap_interval(values: list[float], seed: int, iterations: int) -> list[float]:
    rng = np.random.default_rng(seed)
    samples = rng.choice(np.asarray(values), size=(iterations, len(values)), replace=True)
    return [float(value) for value in np.quantile(samples.mean(axis=1), [0.025, 0.975])]


def _rounded(values: dict[str, float | int]) -> dict[str, float | int]:
    return {
        key: round(value, 6) if isinstance(value, float) else value
        for key, value in values.items()
    }


def _git_commit(project_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _max_rss_megabytes() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    divisor = 1024 * 1024 if sys.platform == "darwin" else 1024
    return float(rss / divisor)


def _save_overlay(
    rgb: np.ndarray,
    prediction: np.ndarray,
    truth: np.ndarray,
    destination: Path,
) -> None:
    output = rgb.astype(np.float32) * 0.58
    predicted = prediction != 0
    expected = truth != 0
    output[predicted & expected] += np.array([46, 204, 113]) * 0.42
    output[predicted & ~expected] += np.array([255, 159, 67]) * 0.42
    output[~predicted & expected] += np.array([255, 64, 129]) * 0.42
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(output, 0, 255).astype(np.uint8)).save(destination, "PNG")


def evaluate_instance_config(config_path: Path, project_root: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Instance evaluation config must use schema_version 1")
    manifest_path = project_root / config["subset_manifest"]
    expected_manifest_sha = config["subset_manifest_sha256"]
    if _sha256_file(manifest_path) != expected_manifest_sha:
        raise ValueError("BBBC038 subset manifest SHA-256 does not match the config")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    rows_config = manifest["images"]
    if len(rows_config) != config["expected_image_count"]:
        raise ValueError("BBBC038 subset image count does not match the config")

    runtime = _load_engine(config, project_root)
    thresholds = [float(value) for value in config["iou_thresholds"]]
    overlay_dir = project_root / config["overlay_dir"] if config.get("overlay_dir") else None
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    total_pixels = 0

    for entry in rows_config:
        image_path = project_root / entry["image_path"]
        mask_dir = project_root / entry["masks_dir"]
        if _sha256_file(image_path) != entry["image_sha256"]:
            raise ValueError(f"Image SHA-256 mismatch: {image_path}")
        if _sha256_mask_tree(mask_dir, project_root) != entry["masks_tree_sha256"]:
            raise ValueError(f"Mask tree SHA-256 mismatch: {entry['image_id']}")
        rgb, grayscale = read_image(image_path)
        truth = load_instance_truth(mask_dir, grayscale.shape)
        if int(truth.max(initial=0)) != entry["truth_instance_count"]:
            raise ValueError(f"Truth instance count mismatch: {entry['image_id']}")

        image_started = time.perf_counter()
        prediction, prediction_metadata = runtime.predict(image_path, grayscale, rgb)
        elapsed = time.perf_counter() - image_started
        prediction, predicted_count = _relabel(prediction)
        truth_count = int(truth.max(initial=0))
        megapixels = float(grayscale.size / 1_000_000)
        total_pixels += grayscale.size
        row: dict[str, Any] = {
            "image_id": entry["image_id"],
            "selection_reason": entry["selection_reason"],
            "width": entry["width"],
            "height": entry["height"],
            "truth_count": truth_count,
            "predicted_count": predicted_count,
            "signed_count_error": predicted_count - truth_count,
            "absolute_count_error": abs(predicted_count - truth_count),
            "absolute_percentage_count_error": abs(predicted_count - truth_count)
            / truth_count,
            **_rounded(_foreground_metrics(prediction, truth)),
            **prediction_metadata,
            "megapixels": round(megapixels, 6),
            "inference_seconds": round(elapsed, 6),
            "seconds_per_megapixel": round(elapsed / megapixels, 6),
        }
        for threshold in thresholds:
            suffix = str(threshold).replace(".", "_")
            metrics = object_metrics(prediction, truth, iou_threshold=threshold)
            row.update(
                {
                    f"object_{key}_iou_{suffix}": value
                    for key, value in _rounded(metrics).items()
                }
            )
        rows.append(row)
        if overlay_dir:
            _save_overlay(
                rgb,
                prediction,
                truth,
                overlay_dir / f"{entry['image_id']}-errors.png",
            )

    iterations = int(config["bootstrap_iterations"])
    seed = int(config["seed"])
    object_results: dict[str, Any] = {}
    for threshold in thresholds:
        suffix = str(threshold).replace(".", "_")
        metric_keys = [
            f"object_precision_iou_{suffix}",
            f"object_recall_iou_{suffix}",
            f"object_f1_iou_{suffix}",
            f"object_mean_matched_iou_iou_{suffix}",
        ]
        totals = {
            name: sum(int(row[f"object_{name}_iou_{suffix}"]) for row in rows)
            for name in ("true_positive", "false_positive", "false_negative")
        }
        object_results[str(threshold)] = {
            "macro": {
                key.removeprefix("object_").removesuffix(f"_iou_{suffix}"): round(
                    float(np.mean([float(row[key]) for row in rows])), 6
                )
                for key in metric_keys
            },
            "pooled": {
                **totals,
                "precision": round(
                    _ratio(
                        totals["true_positive"],
                        totals["true_positive"] + totals["false_positive"],
                    ),
                    6,
                ),
                "recall": round(
                    _ratio(
                        totals["true_positive"],
                        totals["true_positive"] + totals["false_negative"],
                    ),
                    6,
                ),
                "f1": round(
                    _ratio(
                        2 * totals["true_positive"],
                        2 * totals["true_positive"]
                        + totals["false_positive"]
                        + totals["false_negative"],
                    ),
                    6,
                ),
            },
            "macro_bootstrap_95_percent": {
                key.removeprefix("object_").removesuffix(f"_iou_{suffix}"): [
                    round(bound, 6)
                    for bound in _bootstrap_interval(
                        [float(row[key]) for row in rows], seed, iterations
                    )
                ]
                for key in metric_keys
            },
        }

    count_errors = [float(row["absolute_count_error"]) for row in rows]
    percentage_count_errors = [
        float(row["absolute_percentage_count_error"]) for row in rows
    ]
    signed_errors = [float(row["signed_count_error"]) for row in rows]
    pixel_keys = ("pixel_precision", "pixel_recall", "pixel_f1", "pixel_iou")
    total_seconds = time.perf_counter() - started
    report = {
        "schema_version": 1,
        "benchmark_id": config["benchmark_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(project_root),
        "config": str(config_path.relative_to(project_root)),
        "config_sha256": _sha256_file(config_path),
        "subset_manifest": str(manifest_path.relative_to(project_root)),
        "subset_manifest_sha256": expected_manifest_sha,
        "dataset": config["dataset"],
        "engine": runtime.metadata,
        "methodology": {
            "selection": manifest["selection_policy"],
            "matching": "one-to-one maximum-cardinality matching, then maximum IoU",
            "parameter_selection": config["parameter_selection"],
            "bootstrap": {
                "unit": "image",
                "iterations": iterations,
                "seed": seed,
                "confidence": 0.95,
            },
        },
        "results": {
            "image_count": len(rows),
            "truth_instance_count": sum(int(row["truth_count"]) for row in rows),
            "predicted_instance_count": sum(int(row["predicted_count"]) for row in rows),
            "count": {
                "mean_absolute_error": round(float(np.mean(count_errors)), 6),
                "median_absolute_error": round(float(np.median(count_errors)), 6),
                "mean_absolute_percentage_error": round(
                    float(np.mean(percentage_count_errors)), 6
                ),
                "median_absolute_percentage_error": round(
                    float(np.median(percentage_count_errors)), 6
                ),
                "mean_signed_error": round(float(np.mean(signed_errors)), 6),
                "mae_bootstrap_95_percent": [
                    round(bound, 6)
                    for bound in _bootstrap_interval(count_errors, seed, iterations)
                ],
            },
            "objects": object_results,
            "foreground_context_macro": {
                key: round(float(np.mean([float(row[key]) for row in rows])), 6)
                for key in pixel_keys
            },
        },
        "performance": {
            "engine_load_seconds": round(runtime.load_seconds, 6),
            "total_megapixels": round(total_pixels / 1_000_000, 6),
            "total_seconds_including_overlays": round(total_seconds, 6),
            "mean_inference_seconds_per_image": round(
                float(np.mean([row["inference_seconds"] for row in rows])), 6
            ),
            "process_max_rss_mb": round(_max_rss_megabytes(), 3),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "warnings": config["warnings"],
        "per_image": rows,
    }

    json_path = project_root / config["output_json"]
    csv_path = project_root / config["output_csv"]
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with csv_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return report
