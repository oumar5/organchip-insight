"""Evaluate classification comparators on campaign-v2 train/validation only."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import PIL
import sklearn
from PIL import Image

from app.ml.pipeline import AdaptiveSegmentationAnalyzer
from training.ooc_features import (
    EXTRACTOR_VERSION,
    extract_feature_table,
    load_feature_cache,
    write_feature_cache,
)
from training.train_ooc_baseline import (
    PROJECT_ROOT,
    _candidate_models,
    _feature_ranking,
    _git_commit,
    _metrics,
    _select_threshold,
    _sha256,
    _slice_metrics,
)

ALLOWED_SPLITS = {"train", "validation"}


def _load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError("Train/validation manifest is empty")
    splits = {row.get("grouped_split", "") for row in rows}
    if splits != ALLOWED_SPLITS:
        raise ValueError(
            "Comparator manifest must contain train and validation only; "
            f"found {sorted(splits)}"
        )
    paths = [row["path"] for row in rows]
    if len(paths) != len(set(paths)):
        raise ValueError("Comparator manifest contains duplicate paths")
    return rows


def _add_acquisition_metadata(
    rows: list[dict[str, str]], project_root: Path
) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    root = project_root.resolve()
    for row in rows:
        image_path = (root / row["path"]).resolve()
        try:
            image_path.relative_to(root)
        except ValueError as error:
            raise ValueError(f"Image path escapes project root: {row['path']}") from error
        with Image.open(image_path) as image:
            width, height = image.size
            mode = image.mode
        output.append(
            {
                **row,
                "mode": mode,
                "resolution": f"{width}x{height}",
                "mode_resolution": f"{mode}/{width}x{height}",
                "mode_day_bucket": f"{mode}/{row['day_bucket']}",
                "mode_cell_type": f"{mode}/{row['cell_type']}",
            }
        )
    return output


def _categorical_probabilities(
    train_rows: list[dict[str, str]],
    evaluation_rows: list[dict[str, str]],
    *,
    field: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    counts: dict[str, Counter[int]] = defaultdict(Counter)
    global_counts: Counter[int] = Counter()
    for row in train_rows:
        target = int(row["target_index"])
        counts[row[field]][target] += 1
        global_counts[target] += 1
    if not global_counts:
        raise ValueError("Categorical comparator has no training records")

    def probability_good(values: Counter[int]) -> float:
        return (values[1] + 1.0) / (sum(values.values()) + 2.0)

    global_probability = probability_good(global_counts)
    category_probabilities = {
        category: probability_good(values) for category, values in sorted(counts.items())
    }
    evaluation_categories = [row[field] for row in evaluation_rows]
    probabilities = np.asarray(
        [
            category_probabilities.get(category, global_probability)
            for category in evaluation_categories
        ],
        dtype=np.float64,
    )
    details = {
        "feature": field,
        "fit_split": "train",
        "smoothing": "Laplace alpha=1",
        "fixed_threshold": 0.5,
        "global_train_probability_good": round(global_probability, 6),
        "unseen_validation_categories": sorted(
            set(evaluation_categories) - set(category_probabilities)
        ),
        "train_categories": {
            category: {
                "bad": counts[category][0],
                "good": counts[category][1],
                "probability_good": round(category_probabilities[category], 6),
            }
            for category in sorted(counts)
        },
    }
    return probabilities, details


def _evaluation(
    rows: list[dict[str, str]],
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    return {
        "global": _metrics(labels, probabilities, threshold),
        "by_mode": _slice_metrics(rows, labels, probabilities, threshold, "mode"),
        "by_resolution": _slice_metrics(
            rows, labels, probabilities, threshold, "resolution"
        ),
    }


def _fixed_categorical_comparator(
    train_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str]],
    validation_labels: np.ndarray,
    *,
    field: str,
) -> tuple[np.ndarray, dict[str, Any]]:
    probabilities, details = _categorical_probabilities(
        train_rows,
        validation_rows,
        field=field,
    )
    return probabilities, {
        **details,
        "threshold": 0.5,
        "threshold_selection": "fixed before validation evaluation",
        "validation": _evaluation(
            validation_rows,
            validation_labels,
            probabilities,
            0.5,
        ),
    }


def _write_predictions(
    path: Path,
    rows: list[dict[str, str]],
    *,
    majority_probabilities: np.ndarray,
    shortcut_probabilities: np.ndarray,
    mode_day_bucket_probabilities: np.ndarray,
    mode_cell_type_probabilities: np.ndarray,
    handcrafted_probabilities: np.ndarray,
    handcrafted_threshold: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "path",
        "image_id",
        "group_id",
        "target_label",
        "target_index",
        "mode",
        "resolution",
        "majority_probability_good",
        "shortcut_probability_good",
        "mode_day_bucket_probability_good",
        "mode_cell_type_probability_good",
        "handcrafted_probability_good",
        "handcrafted_prediction",
        "handcrafted_correct",
    ]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row, majority, shortcut, mode_day, mode_cell, handcrafted in zip(
            rows,
            majority_probabilities,
            shortcut_probabilities,
            mode_day_bucket_probabilities,
            mode_cell_type_probabilities,
            handcrafted_probabilities,
            strict=True,
        ):
            prediction = int(handcrafted >= handcrafted_threshold)
            target = int(row["target_index"])
            writer.writerow(
                {
                    "path": row["path"],
                    "image_id": row["image_id"],
                    "group_id": row.get("group_id", ""),
                    "target_label": row["target_label"],
                    "target_index": target,
                    "mode": row["mode"],
                    "resolution": row["resolution"],
                    "majority_probability_good": round(float(majority), 8),
                    "shortcut_probability_good": round(float(shortcut), 8),
                    "mode_day_bucket_probability_good": round(float(mode_day), 8),
                    "mode_cell_type_probability_good": round(float(mode_cell), 8),
                    "handcrafted_probability_good": round(float(handcrafted), 8),
                    "handcrafted_prediction": "good" if prediction else "bad",
                    "handcrafted_correct": prediction == target,
                }
            )


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Comparator config must use schema_version 1")
    split_path = PROJECT_ROOT / config["train_validation_csv"]
    _load_manifest(split_path)
    split_sha256 = _sha256(split_path)
    feature_csv = PROJECT_ROOT / config["feature_cache_csv"]
    feature_metadata = PROJECT_ROOT / config["feature_cache_metadata"]
    cache = load_feature_cache(
        feature_csv,
        feature_metadata,
        expected_split_sha256=split_sha256,
        expected_thumbnail_size=int(config["thumbnail_size"]),
        expected_split_path=split_path,
    )
    extraction_started = time.perf_counter()
    if cache is None:
        rows, feature_names = extract_feature_table(
            split_path,
            PROJECT_ROOT,
            thumbnail_size=int(config["thumbnail_size"]),
            workers=int(config["workers"]),
        )
        write_feature_cache(
            rows,
            feature_names,
            feature_csv,
            feature_metadata,
            {
                "split_path": config["train_validation_csv"],
                "split_sha256": split_sha256,
                "thumbnail_size": config["thumbnail_size"],
                "allowed_splits": sorted(ALLOWED_SPLITS),
            },
        )
        feature_cache_reused = False
    else:
        rows, feature_names = cache
        feature_cache_reused = True
    extraction_seconds = time.perf_counter() - extraction_started
    rows = _add_acquisition_metadata(rows, PROJECT_ROOT)

    split_rows = {
        split: [row for row in rows if row["grouped_split"] == split]
        for split in sorted(ALLOWED_SPLITS)
    }
    matrices: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for split, current_rows in split_rows.items():
        features = np.asarray(
            [[float(row[name]) for name in feature_names] for row in current_rows],
            dtype=np.float64,
        )
        labels = np.asarray(
            [int(row["target_index"]) for row in current_rows], dtype=np.int64
        )
        if not np.isfinite(features).all():
            raise ValueError(f"Non-finite feature detected in {split}")
        if len(np.unique(labels)) != 2:
            raise ValueError(f"Split '{split}' must contain both target classes")
        matrices[split] = features, labels

    train_rows = split_rows["train"]
    validation_rows = split_rows["validation"]
    train_features, train_labels = matrices["train"]
    validation_features, validation_labels = matrices["validation"]
    seed = int(config["seed"])
    candidate_results: list[dict[str, Any]] = []
    trained_candidates: list[tuple[str, Any, float, dict[str, Any]]] = []
    for name, model in _candidate_models(config, seed):
        fit_started = time.perf_counter()
        model.fit(train_features, train_labels)
        fit_seconds = time.perf_counter() - fit_started
        probabilities = model.predict_proba(validation_features)[:, 1]
        threshold, selected_metrics = _select_threshold(validation_labels, probabilities)
        fixed_metrics = _metrics(validation_labels, probabilities, 0.5)
        candidate_results.append(
            {
                "name": name,
                "fit_seconds": round(fit_seconds, 6),
                "selected_threshold": round(threshold, 6),
                "fixed_threshold_validation": fixed_metrics,
                "selected_threshold_validation": selected_metrics,
            }
        )
        trained_candidates.append((name, model, threshold, selected_metrics))
        print(
            f"{name}: validation macro-F1={selected_metrics['macro_f1']:.6f}",
            flush=True,
        )
    if not trained_candidates:
        raise ValueError("Comparator config defines no handcrafted candidate")

    selected_name, selected_model, selected_threshold, selected_metrics = max(
        trained_candidates,
        key=lambda item: (
            item[3]["macro_f1"],
            item[3]["balanced_accuracy"],
            item[3]["roc_auc"] or 0.0,
            item[0],
        ),
    )
    handcrafted_probabilities = selected_model.predict_proba(validation_features)[:, 1]
    majority = int(np.mean(train_labels) >= 0.5)
    majority_probabilities = np.full(len(validation_labels), float(majority))
    shortcut_probabilities, shortcut_details = _categorical_probabilities(
        train_rows,
        validation_rows,
        field="mode_resolution",
    )
    shortcut_threshold, shortcut_selected_metrics = _select_threshold(
        validation_labels, shortcut_probabilities
    )
    mode_day_bucket_probabilities, mode_day_bucket_report = (
        _fixed_categorical_comparator(
            train_rows,
            validation_rows,
            validation_labels,
            field="mode_day_bucket",
        )
    )
    mode_cell_type_probabilities, mode_cell_type_report = (
        _fixed_categorical_comparator(
            train_rows,
            validation_rows,
            validation_labels,
            field="mode_cell_type",
        )
    )

    model_path = PROJECT_ROOT / config["model_output"]
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "experiment_id": config["experiment_id"],
            "model": selected_model,
            "model_name": selected_name,
            "threshold": selected_threshold,
            "feature_names": feature_names,
            "extractor_version": EXTRACTOR_VERSION,
            "thumbnail_size": config["thumbnail_size"],
            "label_mapping": {0: "bad", 1: "good"},
            "split_sha256": split_sha256,
        },
        model_path,
    )
    predictions_path = PROJECT_ROOT / config["predictions_output"]
    _write_predictions(
        predictions_path,
        validation_rows,
        majority_probabilities=majority_probabilities,
        shortcut_probabilities=shortcut_probabilities,
        mode_day_bucket_probabilities=mode_day_bucket_probabilities,
        mode_cell_type_probabilities=mode_cell_type_probabilities,
        handcrafted_probabilities=handcrafted_probabilities,
        handcrafted_threshold=selected_threshold,
    )

    report = {
        "schema_version": 1,
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "protocol": {
            "fit_split": "train",
            "evaluation_split": "validation",
            "allowed_splits": sorted(ALLOWED_SPLITS),
            "test_manifest_opened": False,
            "warning": (
                "Validation selects the handcrafted candidate and threshold; these are "
                "decision metrics, not an independent final generalization estimate."
            ),
        },
        "config": {
            "path": str(config_path.relative_to(PROJECT_ROOT)),
            "sha256": _sha256(config_path),
        },
        "split": {
            "path": config["train_validation_csv"],
            "sha256": split_sha256,
            "train_rows": len(train_rows),
            "validation_rows": len(validation_rows),
        },
        "dataset": config["dataset"],
        "features": {
            "extractor_version": EXTRACTOR_VERSION,
            "count": len(feature_names),
            "names": feature_names,
            "thumbnail_size": config["thumbnail_size"],
            "image_only": True,
            "external_weights": False,
            "segmentation_version": AdaptiveSegmentationAnalyzer.version,
            "cache_reused": feature_cache_reused,
            "extraction_seconds": round(extraction_seconds, 6),
            "cache": {
                "csv": {
                    "path": config["feature_cache_csv"],
                    "sha256": _sha256(feature_csv),
                },
                "metadata": {
                    "path": config["feature_cache_metadata"],
                    "sha256": _sha256(feature_metadata),
                },
            },
        },
        "comparators": {
            "majority": {
                "fit_split": "train",
                "majority_label": "good" if majority else "bad",
                "threshold": 0.5,
                "validation": _evaluation(
                    validation_rows,
                    validation_labels,
                    majority_probabilities,
                    0.5,
                ),
            },
            "mode_resolution_shortcut": {
                **shortcut_details,
                "selected_threshold": round(shortcut_threshold, 6),
                "selection_metrics": shortcut_selected_metrics,
                "fixed_threshold_validation": _evaluation(
                    validation_rows,
                    validation_labels,
                    shortcut_probabilities,
                    0.5,
                ),
                "selected_threshold_validation": _evaluation(
                    validation_rows,
                    validation_labels,
                    shortcut_probabilities,
                    shortcut_threshold,
                ),
            },
            "mode_day_bucket_shortcut": mode_day_bucket_report,
            "mode_cell_type_shortcut": mode_cell_type_report,
            "handcrafted": {
                "selection_rule": (
                    "highest validation macro-F1, then balanced accuracy, then ROC-AUC"
                ),
                "candidates": candidate_results,
                "selected_model": selected_name,
                "selected_threshold": round(selected_threshold, 6),
                "selection_metrics": selected_metrics,
                "fixed_threshold_validation": _evaluation(
                    validation_rows,
                    validation_labels,
                    handcrafted_probabilities,
                    0.5,
                ),
                "selected_threshold_validation": _evaluation(
                    validation_rows,
                    validation_labels,
                    handcrafted_probabilities,
                    selected_threshold,
                ),
            },
        },
        "interpretability": {
            "top_handcrafted_features": _feature_ranking(selected_model, feature_names),
            "warning": "Global feature importance is associative, not causal.",
        },
        "artifacts": {
            "model": {
                "path": config["model_output"],
                "sha256": _sha256(model_path),
                "size_bytes": model_path.stat().st_size,
            },
            "predictions": {
                "path": config["predictions_output"],
                "sha256": _sha256(predictions_path),
                "rows": len(validation_rows),
            },
        },
        "implementation": {
            "evaluator": {
                "path": "backend/training/evaluate_ooc_comparators.py",
                "sha256": _sha256(Path(__file__)),
            },
            "feature_extractor": {
                "path": "backend/training/ooc_features.py",
                "sha256": _sha256(PROJECT_ROOT / "backend/training/ooc_features.py"),
            },
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "numpy": np.__version__,
            "pillow": PIL.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
    }
    report_path = PROJECT_ROOT / config["report_output"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    arguments = parser.parse_args()
    config_path = (
        arguments.config
        if arguments.config.is_absolute()
        else PROJECT_ROOT / arguments.config
    )
    report = run(config_path.resolve())
    summary = {
        "majority": report["comparators"]["majority"]["validation"]["global"],
        "mode_resolution_shortcut": report["comparators"]
        ["mode_resolution_shortcut"]["selected_threshold_validation"]["global"],
        "mode_day_bucket_shortcut": report["comparators"]
        ["mode_day_bucket_shortcut"]["validation"]["global"],
        "mode_cell_type_shortcut": report["comparators"]
        ["mode_cell_type_shortcut"]["validation"]["global"],
        "handcrafted": report["comparators"]["handcrafted"]
        ["selected_threshold_validation"]["global"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
