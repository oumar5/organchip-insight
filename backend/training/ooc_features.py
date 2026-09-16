"""Deterministic, image-only features for the OoC quality baseline."""

from __future__ import annotations

import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from app.ml.pipeline import AdaptiveSegmentationAnalyzer

EXTRACTOR_VERSION = "ooc-handcrafted-1.0.0"
METADATA_COLUMNS = {
    "path",
    "image_id",
    "acquisition_prefix",
    "grouped_split",
    "target_label",
    "target_index",
    "cell_type",
    "day_bucket",
    "published_split",
    "sha256",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_thumbnail_size(thumbnail_size: int) -> None:
    if thumbnail_size < 4 or thumbnail_size % 4 != 0:
        raise ValueError("thumbnail_size must be a multiple of 4 and at least 4 pixels")


def _resolve_image_path(project_root: Path, value: str) -> Path:
    relative_path = Path(value)
    if relative_path.is_absolute():
        raise ValueError(f"Image path must be project-relative: {value}")
    root = project_root.resolve()
    image_path = (root / relative_path).resolve()
    try:
        image_path.relative_to(root)
    except ValueError as error:
        raise ValueError(f"Image path escapes the project root: {value}") from error
    return image_path


def _entropy(values: np.ndarray, bins: int = 64) -> float:
    counts, _edges = np.histogram(values, bins=bins, range=(0.0, 1.0))
    probabilities = counts[counts > 0] / counts.sum()
    return float(-np.sum(probabilities * np.log2(probabilities)))


def _safe_ratio(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if abs(denominator) > 1e-12 else 0.0


def extract_image_features(path: Path, *, thumbnail_size: int) -> dict[str, float]:
    _validate_thumbnail_size(thumbnail_size)
    with Image.open(path) as source:
        rgb = np.asarray(
            source.convert("RGB").resize(
                (thumbnail_size, thumbnail_size), Image.Resampling.BILINEAR
            ),
            dtype=np.float32,
        ) / 255.0
    grayscale = (
        0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]
    )
    percentiles = np.percentile(grayscale, [1, 5, 10, 25, 50, 75, 90, 95, 99])
    p01, p05, p10, p25, p50, p75, p90, p95, p99 = percentiles
    dynamic_range = max(float(p99 - p01), 1e-6)
    normalized = np.clip((grayscale - p01) / dynamic_range, 0.0, 1.0)

    gradient_x = np.abs(np.diff(normalized, axis=1))
    gradient_y = np.abs(np.diff(normalized, axis=0))
    gradient = np.concatenate((gradient_x.ravel(), gradient_y.ravel()))
    laplacian = (
        -4.0 * normalized[1:-1, 1:-1]
        + normalized[:-2, 1:-1]
        + normalized[2:, 1:-1]
        + normalized[1:-1, :-2]
        + normalized[1:-1, 2:]
    )

    block_size = thumbnail_size // 4
    block_means: list[float] = []
    block_stds: list[float] = []
    for row in range(4):
        for column in range(4):
            block = normalized[
                row * block_size : (row + 1) * block_size,
                column * block_size : (column + 1) * block_size,
            ]
            block_means.append(float(block.mean()))
            block_stds.append(float(block.std()))

    quarter = thumbnail_size // 4
    center = normalized[:, quarter : 3 * quarter]
    outside = np.concatenate(
        (normalized[:, :quarter].ravel(), normalized[:, 3 * quarter :].ravel())
    )
    saturation = rgb.max(axis=2) - rgb.min(axis=2)
    segmentation = AdaptiveSegmentationAnalyzer().segment(grayscale)
    areas = np.bincount(segmentation.labels.ravel())[1:]
    foreground_fraction = float(segmentation.mask.mean())

    return {
        "intensity_mean": float(grayscale.mean()),
        "intensity_std": float(grayscale.std()),
        "intensity_p01": float(p01),
        "intensity_p05": float(p05),
        "intensity_p10": float(p10),
        "intensity_p25": float(p25),
        "intensity_p50": float(p50),
        "intensity_p75": float(p75),
        "intensity_p90": float(p90),
        "intensity_p95": float(p95),
        "intensity_p99": float(p99),
        "intensity_iqr": float(p75 - p25),
        "intensity_dynamic_range": float(p99 - p01),
        "entropy_64": _entropy(grayscale),
        "dark_fraction_005": float(np.mean(grayscale < 0.05)),
        "dark_fraction_010": float(np.mean(grayscale < 0.10)),
        "bright_fraction_090": float(np.mean(grayscale > 0.90)),
        "bright_fraction_095": float(np.mean(grayscale > 0.95)),
        "gradient_mean": float(gradient.mean()),
        "gradient_std": float(gradient.std()),
        "gradient_p90": float(np.percentile(gradient, 90)),
        "gradient_p99": float(np.percentile(gradient, 99)),
        "gradient_edge_fraction_010": float(np.mean(gradient > 0.10)),
        "gradient_orientation_ratio": _safe_ratio(
            float(gradient_x.mean()), float(gradient_y.mean())
        ),
        "laplacian_variance": float(laplacian.var()),
        "laplacian_abs_mean": float(np.abs(laplacian).mean()),
        "laplacian_abs_p95": float(np.percentile(np.abs(laplacian), 95)),
        "block_mean_std": float(np.std(block_means)),
        "block_mean_range": float(max(block_means) - min(block_means)),
        "block_std_mean": float(np.mean(block_stds)),
        "block_std_std": float(np.std(block_stds)),
        "center_mean": float(center.mean()),
        "center_std": float(center.std()),
        "outside_mean": float(outside.mean()),
        "outside_std": float(outside.std()),
        "center_outside_mean_delta": float(center.mean() - outside.mean()),
        "center_outside_std_ratio": _safe_ratio(float(center.std()), float(outside.std())),
        "saturation_mean": float(saturation.mean()),
        "saturation_std": float(saturation.std()),
        "saturation_fraction_005": float(np.mean(saturation > 0.05)),
        "red_mean": float(rgb[:, :, 0].mean()),
        "green_mean": float(rgb[:, :, 1].mean()),
        "blue_mean": float(rgb[:, :, 2].mean()),
        "segmentation_threshold": float(segmentation.threshold),
        "segmentation_polarity_dark": float(segmentation.polarity == "dark"),
        "segmentation_foreground_fraction": foreground_fraction,
        "segmentation_object_count": float(len(areas)),
        "segmentation_area_mean": float(areas.mean()) if len(areas) else 0.0,
        "segmentation_area_median": float(np.median(areas)) if len(areas) else 0.0,
        "segmentation_area_p90": float(np.percentile(areas, 90)) if len(areas) else 0.0,
    }


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def extract_feature_table(
    split_path: Path,
    project_root: Path,
    *,
    thumbnail_size: int,
    workers: int,
) -> tuple[list[dict[str, Any]], list[str]]:
    _validate_thumbnail_size(thumbnail_size)
    if workers < 1:
        raise ValueError("workers must be at least 1")
    split_records = _read_csv(split_path)
    if not split_records:
        raise ValueError("Split manifest contains no records")
    missing_columns = METADATA_COLUMNS - set(split_records[0])
    if missing_columns:
        raise ValueError(
            "Split manifest is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )
    manifest_paths = [record["path"] for record in split_records]
    if len(manifest_paths) != len(set(manifest_paths)):
        raise ValueError("Split manifest contains duplicate image paths")

    def extract(record: dict[str, str]) -> tuple[dict[str, Any], dict[str, float]]:
        image_path = _resolve_image_path(project_root, record["path"])
        actual_sha256 = _sha256(image_path)
        if actual_sha256 != record["sha256"]:
            raise ValueError(
                f"Image checksum mismatch for {record['path']}: "
                f"expected {record['sha256']}, got {actual_sha256}"
            )
        features = extract_image_features(
            image_path, thumbnail_size=thumbnail_size
        )
        return record, features

    output: list[dict[str, Any]] = []
    feature_names: list[str] | None = None
    with ThreadPoolExecutor(max_workers=workers) as executor:
        for index, (record, features) in enumerate(executor.map(extract, split_records), start=1):
            current_feature_names = sorted(features)
            if feature_names is None:
                feature_names = current_feature_names
            elif current_feature_names != feature_names:
                raise ValueError("Feature schema changed while extracting the dataset")
            output.append({**record, **features})
            if index % 250 == 0 or index == len(split_records):
                print(f"Extracted features for {index}/{len(split_records)} images", flush=True)

    if feature_names is None:
        raise ValueError("No features were extracted")
    return output, feature_names


def write_feature_cache(
    rows: list[dict[str, Any]],
    feature_names: list[str],
    csv_path: Path,
    metadata_path: Path,
    metadata: dict[str, Any],
) -> None:
    if not rows:
        raise ValueError("Cannot write an empty feature cache")
    if not feature_names:
        raise ValueError("Cannot write a feature cache without features")
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path",
        "image_id",
        "acquisition_prefix",
        "grouped_split",
        "target_label",
        "target_index",
        "cell_type",
        "day_bucket",
        "published_split",
        "sha256",
        *feature_names,
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    metadata_path.write_text(
        json.dumps(
            {
                **metadata,
                "extractor_version": EXTRACTOR_VERSION,
                "segmentation_version": AdaptiveSegmentationAnalyzer.version,
                "feature_names": feature_names,
                "rows": len(rows),
                "feature_csv_sha256": _sha256(csv_path),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )


def load_feature_cache(
    csv_path: Path,
    metadata_path: Path,
    *,
    expected_split_sha256: str,
    expected_thumbnail_size: int,
    expected_split_path: Path,
) -> tuple[list[dict[str, str]], list[str]] | None:
    if not csv_path.is_file() or not metadata_path.is_file():
        return None
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if metadata.get("extractor_version") != EXTRACTOR_VERSION:
        return None
    if metadata.get("segmentation_version") != AdaptiveSegmentationAnalyzer.version:
        return None
    if metadata.get("split_sha256") != expected_split_sha256:
        return None
    if metadata.get("thumbnail_size") != expected_thumbnail_size:
        return None
    feature_names = metadata.get("feature_names")
    if (
        not isinstance(feature_names, list)
        or not feature_names
        or not all(isinstance(name, str) and name for name in feature_names)
        or len(feature_names) != len(set(feature_names))
    ):
        return None
    expected_csv_sha256 = metadata.get("feature_csv_sha256")
    if not isinstance(expected_csv_sha256, str) or _sha256(csv_path) != expected_csv_sha256:
        return None
    try:
        rows = _read_csv(csv_path)
        split_rows = _read_csv(expected_split_path)
    except (OSError, csv.Error):
        return None
    if len(rows) != metadata.get("rows"):
        return None
    if len(rows) != len(split_rows) or not rows:
        return None
    required_columns = METADATA_COLUMNS | set(feature_names)
    for cached_row, split_row in zip(rows, split_rows, strict=True):
        if not required_columns.issubset(cached_row):
            return None
        if any(cached_row[column] != split_row[column] for column in METADATA_COLUMNS):
            return None
    return rows, list(feature_names)
