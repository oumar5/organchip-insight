"""Evaluate the frozen adaptive engine on iOrganoAssay v1.1.0 validation images."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import resource
import subprocess
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.benchmark import foreground_metrics
from app.ml.pipeline import AdaptiveSegmentationAnalyzer

PROJECT_ROOT = Path(__file__).resolve().parents[2]
METRIC_NAMES = ("precision", "recall", "f1", "iou", "centroid_error")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_binary_mask(path: Path, threshold: float) -> np.ndarray:
    with Image.open(path) as image:
        grayscale = np.asarray(image.convert("L"), dtype=np.float32) / 255.0
    return grayscale > threshold


def centroid_error(prediction: np.ndarray, truth: np.ndarray) -> float | None:
    predicted_coordinates = np.argwhere(prediction)
    truth_coordinates = np.argwhere(truth)
    if not len(predicted_coordinates) or not len(truth_coordinates):
        return None
    distance = float(
        np.linalg.norm(predicted_coordinates.mean(axis=0) - truth_coordinates.mean(axis=0))
    )
    diagonal = float(np.hypot(*truth.shape))
    return distance / diagonal if diagonal else 0.0


def mask_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float | int | None]:
    metrics: dict[str, float | int | None] = foreground_metrics(prediction, truth)
    metrics["centroid_error"] = centroid_error(prediction, truth)
    return metrics


def _verify_record(record: dict[str, Any], project_root: Path) -> Path:
    path = project_root / record["path"]
    if not path.is_file():
        raise FileNotFoundError(f"Missing validation file: {path}")
    if path.stat().st_size != record["size_bytes"]:
        raise ValueError(f"Size mismatch for {path}")
    if sha256_file(path) != record["sha256"]:
        raise ValueError(f"SHA-256 mismatch for {path}")
    return path


def _mean(rows: list[dict[str, Any]], prefix: str, metric: str) -> float | None:
    values = [
        float(row[f"{prefix}_{metric}"])
        for row in rows
        if row[f"{prefix}_{metric}"] is not None
    ]
    return float(np.mean(values)) if values else None


def _rounded(value: float | int | None) -> float | int | None:
    return round(value, 6) if isinstance(value, float) else value


def _summary(rows: list[dict[str, Any]], prefix: str) -> dict[str, float | None]:
    return {metric: _rounded(_mean(rows, prefix, metric)) for metric in METRIC_NAMES}


def _bootstrap_interval(values: list[float], seed: int, iterations: int) -> list[float]:
    rng = np.random.default_rng(seed)
    samples = rng.choice(np.asarray(values), size=(iterations, len(values)), replace=True)
    means = samples.mean(axis=1)
    return [round(float(value), 6) for value in np.quantile(means, [0.025, 0.975])]


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
    output[prediction & truth] += np.array([46, 204, 113]) * 0.42
    output[prediction & ~truth] += np.array([255, 159, 67]) * 0.42
    output[~prediction & truth] += np.array([255, 64, 129]) * 0.42
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(output, 0, 255).astype(np.uint8)).save(destination, "PNG")


def evaluate(config_path: Path, project_root: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Evaluation config must use schema_version 1")
    manifest_path = project_root / config["manifest"]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("manifest_id") != "iorganoassay-validation-v1.1.0":
        raise ValueError("Unexpected iOrganoAssay manifest")

    threshold = float(config["ground_truth_threshold"])
    if threshold != 0.5:
        raise ValueError("The preregistered iOrganoAssay threshold is 0.5")
    analyzer = AdaptiveSegmentationAnalyzer()
    rows: list[dict[str, Any]] = []
    inference_seconds: list[float] = []
    overlay_dir = project_root / config["overlay_dir"]
    started = time.perf_counter()

    for sample in manifest["samples"]:
        files = sample["files"]
        brightfield_path = _verify_record(files["brightfield"], project_root)
        truth_path = _verify_record(files["ground_truth"], project_root)
        reference_path = _verify_record(files["reference_segmentation"], project_root)

        truth = load_binary_mask(truth_path, threshold)
        reference = load_binary_mask(reference_path, threshold)
        target_size = (truth.shape[1], truth.shape[0])
        with Image.open(brightfield_path) as source:
            resized = source.convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
            rgb = np.asarray(resized)
            grayscale = np.asarray(resized.convert("L"), dtype=np.float32) / 255.0

        image_started = time.perf_counter()
        segmentation = analyzer.segment(grayscale)
        inference_seconds.append(time.perf_counter() - image_started)
        adaptive = segmentation.mask.astype(bool, copy=False)
        adaptive_metrics = mask_metrics(adaptive, truth)
        reference_metrics = mask_metrics(reference, truth)
        row: dict[str, Any] = {
            "sample_id": sample["sample_id"],
            "condition": sample["condition"],
            "width": target_size[0],
            "height": target_size[1],
            "truth_foreground_fraction": round(float(truth.mean()), 6),
            "adaptive_foreground_fraction": round(float(adaptive.mean()), 6),
            "reference_foreground_fraction": round(float(reference.mean()), 6),
            "adaptive_threshold": round(segmentation.threshold, 6),
            "adaptive_polarity": segmentation.polarity,
        }
        row.update({f"adaptive_{key}": _rounded(value) for key, value in adaptive_metrics.items()})
        row.update(
            {f"reference_{key}": _rounded(value) for key, value in reference_metrics.items()}
        )
        rows.append(row)
        _save_overlay(
            rgb,
            adaptive,
            truth,
            overlay_dir / f"{sample['sample_id']}-adaptive-errors.png",
        )

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[row["condition"]].append(row)

    criteria = config["decision_criteria"]
    overall_adaptive = _summary(rows, "adaptive")
    condition_adaptive = {
        condition: _summary(condition_rows, "adaptive")
        for condition, condition_rows in sorted(grouped.items())
    }
    fraction_below = float(
        np.mean([float(row["adaptive_f1"]) < 0.5 for row in rows])
    )
    decisions = {
        "overall_macro_f1": overall_adaptive["f1"] >= criteria["minimum_macro_f1"],
        "condition_macro_f1": all(
            summary["f1"] >= criteria["minimum_condition_macro_f1"]
            for summary in condition_adaptive.values()
        ),
        "fraction_below_f1_0_5": fraction_below
        <= criteria["maximum_fraction_below_f1_0_5"],
    }

    iterations = int(config["bootstrap_iterations"])
    seed = int(config["seed"])
    total_seconds = time.perf_counter() - started
    report = {
        "schema_version": 1,
        "benchmark_id": config["benchmark_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(project_root),
        "config": str(config_path.relative_to(project_root)),
        "config_sha256": sha256_file(config_path),
        "manifest": str(manifest_path.relative_to(project_root)),
        "manifest_sha256": sha256_file(manifest_path),
        "dataset": manifest["dataset"],
        "methodology": {
            "sample_selection": "all 28 official v1.1.0 validation triples",
            "conditions": manifest["conditions"],
            "ground_truth": (
                "official GT JPEG converted to grayscale and thresholded above 0.5, "
                "matching the published R application"
            ),
            "input_adapter": (
                "brightfield RGB resized once to the GT dimensions with Pillow LANCZOS; "
                "the frozen adaptive segmentation algorithm is otherwise unchanged"
            ),
            "reference": (
                "official Seg JPEG thresholded by the same published 0.5 rule; contextual "
                "reference, not a competing model rerun"
            ),
            "parameter_selection": config["parameter_selection"],
            "bootstrap": {
                "unit": "image",
                "iterations": iterations,
                "seed": seed,
                "confidence": 0.95,
            },
        },
        "engine": {
            "id": "adaptive-segmentation-v1",
            "version": analyzer.version,
            "training_required": False,
        },
        "results": {
            "image_count": len(rows),
            "adaptive_macro": overall_adaptive,
            "adaptive_macro_by_condition": condition_adaptive,
            "adaptive_macro_f1_bootstrap_95_percent": _bootstrap_interval(
                [float(row["adaptive_f1"]) for row in rows], seed, iterations
            ),
            "adaptive_fraction_below_f1_0_5": round(fraction_below, 6),
            "reference_macro": _summary(rows, "reference"),
            "reference_macro_by_condition": {
                condition: _summary(condition_rows, "reference")
                for condition, condition_rows in sorted(grouped.items())
            },
        },
        "decision": {
            "criteria": criteria,
            "criteria_passed": decisions,
            "eligible_as_external_organoid_evidence": all(decisions.values()),
            "effect_on_product": (
                "Evidence only: this benchmark never changes the frozen engine or opens "
                "the OoC classification test."
            ),
        },
        "performance": {
            "mean_adaptive_inference_seconds_per_image": round(
                float(np.mean(inference_seconds)), 6
            ),
            "total_seconds_including_hashes_and_overlays": round(total_seconds, 6),
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
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    with csv_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=PROJECT_ROOT
        / "backend/evaluation/configs/iorganoassay-validation-v1.1.0-adaptive.json",
    )
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    report = evaluate(config_path.resolve(), PROJECT_ROOT)
    print(json.dumps({"results": report["results"], "decision": report["decision"]}, indent=2))


if __name__ == "__main__":
    main()
