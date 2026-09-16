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

from app.ml.pipeline import AdaptiveSegmentationAnalyzer


def _ratio(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0


def foreground_metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float | int]:
    prediction = prediction.astype(bool, copy=False)
    truth = truth.astype(bool, copy=False)
    if prediction.shape != truth.shape:
        raise ValueError(f"Mask shape mismatch: prediction={prediction.shape}, truth={truth.shape}")

    true_positive = int(np.count_nonzero(prediction & truth))
    false_positive = int(np.count_nonzero(prediction & ~truth))
    false_negative = int(np.count_nonzero(~prediction & truth))
    true_negative = int(np.count_nonzero(~prediction & ~truth))
    precision = _ratio(true_positive, true_positive + false_positive)
    recall = _ratio(true_positive, true_positive + false_negative)
    return {
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": precision,
        "recall": recall,
        "f1": _ratio(2 * true_positive, 2 * true_positive + false_positive + false_negative),
        "iou": _ratio(true_positive, true_positive + false_positive + false_negative),
    }


def _load_truth(path: Path) -> np.ndarray:
    with Image.open(path) as image:
        values = np.asarray(image)
    if values.ndim == 3:
        values = np.any(values > 0, axis=2)
    return values > 0


def _save_error_overlay(
    rgb: np.ndarray,
    prediction: np.ndarray,
    truth: np.ndarray,
    destination: Path,
) -> None:
    output = rgb.astype(np.float32) * 0.58
    true_positive = prediction & truth
    false_positive = prediction & ~truth
    false_negative = ~prediction & truth
    output[true_positive] += np.array([46, 204, 113]) * 0.42
    output[false_positive] += np.array([255, 159, 67]) * 0.42
    output[false_negative] += np.array([255, 64, 129]) * 0.42
    destination.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.clip(output, 0, 255).astype(np.uint8)).save(destination, "PNG")


def _bootstrap_interval(
    values: list[float],
    *,
    seed: int,
    iterations: int,
) -> list[float]:
    if not values:
        return [0.0, 0.0]
    rng = np.random.default_rng(seed)
    samples = rng.choice(np.asarray(values), size=(iterations, len(values)), replace=True)
    means = samples.mean(axis=1)
    return [float(value) for value in np.quantile(means, [0.025, 0.975])]


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


def _rounded(metrics: dict[str, float | int]) -> dict[str, float | int]:
    return {
        key: round(value, 6) if isinstance(value, float) else value
        for key, value in metrics.items()
    }


def evaluate_config(config_path: Path, project_root: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Evaluation config must use schema_version 1")
    if config.get("engine") != "adaptive-segmentation-v1":
        raise ValueError(f"Unsupported engine: {config.get('engine')}")

    images_dir = project_root / config["images_dir"]
    masks_dir = project_root / config["masks_dir"]
    image_paths = sorted(images_dir.glob(config.get("image_glob", "*.tif")))
    if not image_paths:
        raise FileNotFoundError(f"No evaluation images found in {images_dir}")

    analyzer = AdaptiveSegmentationAnalyzer()
    overlay_dir = project_root / config["overlay_dir"] if config.get("overlay_dir") else None
    rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    total_pixels = 0

    for image_path in image_paths:
        mask_name = config["mask_template"].format(stem=image_path.stem)
        mask_path = masks_dir / mask_name
        if not mask_path.is_file():
            raise FileNotFoundError(f"Missing ground-truth mask for {image_path.name}: {mask_path}")

        with Image.open(image_path) as source:
            rgb = np.asarray(source.convert("RGB"), dtype=np.uint8)
            grayscale = np.asarray(source.convert("L"), dtype=np.float32) / 255.0
        truth = _load_truth(mask_path)

        image_started = time.perf_counter()
        segmentation = analyzer.segment(grayscale)
        elapsed = time.perf_counter() - image_started
        metrics = foreground_metrics(segmentation.mask, truth)
        megapixels = float(grayscale.size / 1_000_000)
        total_pixels += grayscale.size
        row = {
            "image": image_path.name,
            **_rounded(metrics),
            "truth_foreground_fraction": round(float(truth.mean()), 6),
            "predicted_foreground_fraction": round(float(segmentation.mask.mean()), 6),
            "threshold": round(segmentation.threshold, 6),
            "polarity": segmentation.polarity,
            "megapixels": round(megapixels, 6),
            "inference_seconds": round(elapsed, 6),
            "seconds_per_megapixel": round(elapsed / megapixels, 6),
        }
        rows.append(row)

        if overlay_dir:
            _save_error_overlay(
                rgb,
                segmentation.mask,
                truth,
                overlay_dir / f"{image_path.stem}-errors.png",
            )

    total_seconds = time.perf_counter() - started
    metric_names = ("precision", "recall", "f1", "iou")
    macro = {
        name: float(np.mean([float(row[name]) for row in rows])) for name in metric_names
    }
    totals = {
        name: sum(int(row[name]) for row in rows)
        for name in ("true_positive", "false_positive", "false_negative", "true_negative")
    }
    micro_precision = _ratio(
        totals["true_positive"], totals["true_positive"] + totals["false_positive"]
    )
    micro_recall = _ratio(
        totals["true_positive"], totals["true_positive"] + totals["false_negative"]
    )
    micro = {
        **totals,
        "precision": micro_precision,
        "recall": micro_recall,
        "f1": _ratio(
            2 * totals["true_positive"],
            2 * totals["true_positive"]
            + totals["false_positive"]
            + totals["false_negative"],
        ),
        "iou": _ratio(
            totals["true_positive"],
            totals["true_positive"]
            + totals["false_positive"]
            + totals["false_negative"],
        ),
    }

    iterations = int(config.get("bootstrap_iterations", 10_000))
    seed = int(config.get("seed", 20260916))
    intervals = {
        name: _bootstrap_interval(
            [float(row[name]) for row in rows], seed=seed, iterations=iterations
        )
        for name in metric_names
    }
    config_sha256 = hashlib.sha256(config_path.read_bytes()).hexdigest()
    report = {
        "schema_version": 1,
        "benchmark_id": config["benchmark_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(project_root),
        "config": str(config_path.relative_to(project_root)),
        "config_sha256": config_sha256,
        "dataset": config["dataset"],
        "engine": {
            "id": config["engine"],
            "version": analyzer.version,
            "training_required": False,
        },
        "methodology": {
            "ground_truth": "non-zero pixels in the official manual PNG masks",
            "aggregation": "macro is the unweighted mean across images; micro pools pixels",
            "bootstrap": {
                "unit": "image",
                "iterations": iterations,
                "seed": seed,
                "confidence": 0.95,
            },
        },
        "results": {
            "image_count": len(rows),
            "macro": _rounded(macro),
            "micro": _rounded(micro),
            "macro_bootstrap_95_percent": {
                name: [round(bound, 6) for bound in bounds]
                for name, bounds in intervals.items()
            },
            "median_f1": round(float(np.median([row["f1"] for row in rows])), 6),
        },
        "performance": {
            "total_megapixels": round(total_pixels / 1_000_000, 6),
            "total_seconds_including_overlays": round(total_seconds, 6),
            "mean_inference_seconds_per_image": round(
                float(np.mean([row["inference_seconds"] for row in rows])), 6
            ),
            "mean_inference_seconds_per_megapixel": round(
                float(np.mean([row["seconds_per_megapixel"] for row in rows])), 6
            ),
            "process_max_rss_mb": round(_max_rss_megabytes(), 3),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
        },
        "historical_references": config.get("historical_references", []),
        "warnings": [
            "This external dataset is DIC microfluidics, not the challenge's OoC dataset.",
            "The 95% intervals resample images, not independent biological experiments.",
            "Historical values are contextual unless preprocessing and masks are identical.",
        ],
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
