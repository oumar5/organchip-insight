"""Train and evaluate a leakage-aware, image-only OoC quality baseline."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import platform
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import PIL
import skimage
import sklearn
from sklearn.ensemble import ExtraTreesClassifier, HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from app.ml.pipeline import AdaptiveSegmentationAnalyzer
from training.ooc_features import (
    EXTRACTOR_VERSION,
    extract_feature_table,
    load_feature_cache,
    write_feature_cache,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def _metrics(labels: np.ndarray, probabilities: np.ndarray, threshold: float) -> dict[str, Any]:
    predictions = (probabilities >= threshold).astype(np.int64)
    class_counts = {
        "bad": int(np.sum(labels == 0)),
        "good": int(np.sum(labels == 1)),
    }
    both_classes_present = all(class_counts.values())
    result: dict[str, Any] = {
        "support": int(len(labels)),
        "class_counts": class_counts,
        "both_classes_present": both_classes_present,
        "positive_rate": round(float(labels.mean()), 6),
        "predicted_positive_rate": round(float(predictions.mean()), 6),
        "threshold": round(float(threshold), 6),
        "accuracy": round(float(accuracy_score(labels, predictions)), 6),
        "balanced_accuracy": (
            round(float(balanced_accuracy_score(labels, predictions)), 6)
            if both_classes_present
            else None
        ),
        "precision_good": round(
            float(precision_score(labels, predictions, zero_division=0)), 6
        ),
        "recall_good": round(float(recall_score(labels, predictions, zero_division=0)), 6),
        "f1_good": round(float(f1_score(labels, predictions, zero_division=0)), 6),
        "macro_f1": (
            round(float(f1_score(labels, predictions, average="macro", zero_division=0)), 6)
            if both_classes_present
            else None
        ),
        "brier_score": round(float(brier_score_loss(labels, probabilities)), 6),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
    }
    result["roc_auc"] = (
        round(float(roc_auc_score(labels, probabilities)), 6)
        if both_classes_present
        else None
    )
    return result


def _select_threshold(
    labels: np.ndarray, probabilities: np.ndarray
) -> tuple[float, dict[str, Any]]:
    if len(np.unique(labels)) != 2:
        raise ValueError("Threshold selection requires both target classes")
    candidates = np.linspace(0.05, 0.95, 181)
    scored = [
        (_metrics(labels, probabilities, float(threshold)), threshold)
        for threshold in candidates
    ]
    best_metrics, best_threshold = max(
        scored,
        key=lambda item: (
            item[0]["macro_f1"],
            item[0]["balanced_accuracy"],
            -abs(float(item[1]) - 0.5),
        ),
    )
    return float(best_threshold), best_metrics


def _candidate_models(config: dict[str, Any], seed: int) -> list[tuple[str, Any]]:
    candidates: list[tuple[str, Any]] = []
    for value in config["models"]["logistic_regression"]["c_values"]:
        candidates.append(
            (
                f"logistic-regression-c{value}",
                Pipeline(
                    [
                        ("scale", StandardScaler()),
                        (
                            "classifier",
                            LogisticRegression(
                                C=float(value),
                                class_weight="balanced",
                                max_iter=5000,
                                random_state=seed,
                            ),
                        ),
                    ]
                ),
            )
        )
    for item in config["models"]["extra_trees"]:
        depth = item["max_depth"]
        candidates.append(
            (
                f"extra-trees-depth{depth}-leaf{item['min_samples_leaf']}",
                ExtraTreesClassifier(
                    n_estimators=int(item["n_estimators"]),
                    max_depth=None if depth is None else int(depth),
                    min_samples_leaf=int(item["min_samples_leaf"]),
                    class_weight="balanced",
                    random_state=seed,
                    n_jobs=-1,
                ),
            )
        )
    for item in config["models"]["hist_gradient_boosting"]:
        candidates.append(
            (
                (
                    f"hist-gradient-leaves{item['max_leaf_nodes']}"
                    f"-l2-{item['l2_regularization']}"
                ),
                HistGradientBoostingClassifier(
                    learning_rate=float(item["learning_rate"]),
                    max_iter=int(item["max_iter"]),
                    max_leaf_nodes=int(item["max_leaf_nodes"]),
                    l2_regularization=float(item["l2_regularization"]),
                    class_weight="balanced",
                    random_state=seed,
                ),
            )
        )
    return candidates


def _bootstrap_by_group(
    labels: np.ndarray,
    probabilities: np.ndarray,
    groups: np.ndarray,
    threshold: float,
    *,
    iterations: int,
    seed: int,
) -> dict[str, list[float]]:
    unique_groups = np.unique(groups)
    group_indices = {group: np.flatnonzero(groups == group) for group in unique_groups}
    rng = np.random.default_rng(seed)
    values: dict[str, list[float]] = {
        "accuracy": [],
        "balanced_accuracy": [],
        "macro_f1": [],
        "roc_auc": [],
    }
    for _iteration in range(iterations):
        sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
        indices = np.concatenate([group_indices[group] for group in sampled_groups])
        metrics = _metrics(labels[indices], probabilities[indices], threshold)
        for name in values:
            value = metrics[name]
            if value is not None:
                values[name].append(float(value))
    return {
        name: [
            round(float(bound), 6)
            for bound in np.quantile(metric_values, [0.025, 0.975])
        ]
        for name, metric_values in values.items()
        if metric_values
    }


def _slice_metrics(
    rows: list[dict[str, str]],
    labels: np.ndarray,
    probabilities: np.ndarray,
    threshold: float,
    field: str,
) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    values = np.asarray([row[field] for row in rows])
    for value in sorted(set(values)):
        indices = np.flatnonzero(values == value)
        output[str(value)] = _metrics(labels[indices], probabilities[indices], threshold)
    return output


def _feature_ranking(model: Any, feature_names: list[str]) -> list[dict[str, Any]]:
    if isinstance(model, Pipeline):
        values = np.abs(model.named_steps["classifier"].coef_[0])
    elif hasattr(model, "feature_importances_"):
        values = np.asarray(model.feature_importances_)
    else:
        return []
    order = np.argsort(values)[::-1]
    return [
        {"feature": feature_names[index], "importance": round(float(values[index]), 8)}
        for index in order[:20]
    ]


def _write_predictions(
    path: Path,
    rows: list[dict[str, str]],
    probabilities: np.ndarray,
    threshold: float,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        fieldnames = [
            "path",
            "image_id",
            "acquisition_prefix",
            "target_label",
            "target_index",
            "probability_good",
            "predicted_label",
            "correct",
            "cell_type",
            "day_bucket",
        ]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for row, probability in zip(rows, probabilities, strict=True):
            prediction = int(probability >= threshold)
            target = int(row["target_index"])
            writer.writerow(
                {
                    "path": row["path"],
                    "image_id": row["image_id"],
                    "acquisition_prefix": row["acquisition_prefix"],
                    "target_label": row["target_label"],
                    "target_index": target,
                    "probability_good": round(float(probability), 8),
                    "predicted_label": "good" if prediction else "bad",
                    "correct": prediction == target,
                    "cell_type": row["cell_type"],
                    "day_bucket": row["day_bucket"],
                }
            )


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Training config must use schema_version 1")
    split_path = PROJECT_ROOT / config["split_csv"]
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
                "split_path": config["split_csv"],
                "split_sha256": split_sha256,
                "thumbnail_size": config["thumbnail_size"],
            },
        )
        feature_cache_reused = False
    else:
        rows, feature_names = cache
        feature_cache_reused = True
    extraction_seconds = time.perf_counter() - extraction_started

    matrices: dict[str, tuple[list[dict[str, str]], np.ndarray, np.ndarray]] = {}
    for split in ("train", "validation", "test"):
        split_rows = [row for row in rows if row["grouped_split"] == split]
        features = np.asarray(
            [[float(row[name]) for name in feature_names] for row in split_rows],
            dtype=np.float64,
        )
        labels = np.asarray([int(row["target_index"]) for row in split_rows], dtype=np.int64)
        if not np.isfinite(features).all():
            raise ValueError(f"Non-finite feature detected in {split}")
        if len(np.unique(labels)) != 2:
            raise ValueError(f"Split '{split}' must contain both target classes")
        matrices[split] = split_rows, features, labels

    train_rows, train_features, train_labels = matrices["train"]
    validation_rows, validation_features, validation_labels = matrices["validation"]
    test_rows, test_features, test_labels = matrices["test"]
    seed = int(config["seed"])
    candidate_results: list[dict[str, Any]] = []
    trained_candidates: list[tuple[str, Any, float, dict[str, Any]]] = []
    for name, model in _candidate_models(config, seed):
        fit_started = time.perf_counter()
        model.fit(train_features, train_labels)
        fit_seconds = time.perf_counter() - fit_started
        validation_probabilities = model.predict_proba(validation_features)[:, 1]
        threshold, validation_metrics = _select_threshold(
            validation_labels, validation_probabilities
        )
        candidate = {
            "name": name,
            "fit_seconds": round(fit_seconds, 6),
            "selected_threshold": round(threshold, 6),
            "validation": validation_metrics,
        }
        candidate_results.append(candidate)
        trained_candidates.append((name, model, threshold, validation_metrics))
        print(
            f"{name}: validation macro-F1={validation_metrics['macro_f1']:.6f}",
            flush=True,
        )

    selected_name, selected_model, threshold, selected_validation = max(
        trained_candidates,
        key=lambda item: (
            item[3]["macro_f1"],
            item[3]["balanced_accuracy"],
            item[3]["roc_auc"] or 0.0,
            item[0],
        ),
    )
    test_probabilities = selected_model.predict_proba(test_features)[:, 1]
    test_metrics = _metrics(test_labels, test_probabilities, threshold)
    test_groups = np.asarray([row["acquisition_prefix"] for row in test_rows])
    bootstrap = _bootstrap_by_group(
        test_labels,
        test_probabilities,
        test_groups,
        threshold,
        iterations=int(config["bootstrap_iterations"]),
        seed=seed,
    )

    majority = int(np.mean(train_labels) >= 0.5)
    majority_probabilities = np.full(len(test_labels), float(majority))
    majority_metrics = _metrics(test_labels, majority_probabilities, 0.5)

    model_path = PROJECT_ROOT / config["model_output"]
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "experiment_id": config["experiment_id"],
            "model": selected_model,
            "model_name": selected_name,
            "threshold": threshold,
            "feature_names": feature_names,
            "extractor_version": EXTRACTOR_VERSION,
            "thumbnail_size": config["thumbnail_size"],
            "label_mapping": {0: "bad", 1: "good"},
            "split_sha256": split_sha256,
        },
        model_path,
    )
    predictions_path = PROJECT_ROOT / config["predictions_output"]
    _write_predictions(predictions_path, test_rows, test_probabilities, threshold)

    report = {
        "schema_version": 1,
        "experiment_id": config["experiment_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "implementation": {
            "trainer": {
                "path": "backend/training/train_ooc_baseline.py",
                "sha256": _sha256(Path(__file__)),
            },
            "feature_extractor": {
                "path": "backend/training/ooc_features.py",
                "sha256": _sha256(PROJECT_ROOT / "backend/training/ooc_features.py"),
                "version": EXTRACTOR_VERSION,
            },
        },
        "config": str(config_path.relative_to(PROJECT_ROOT)),
        "config_sha256": _sha256(config_path),
        "split": {
            "path": config["split_csv"],
            "sha256": split_sha256,
            "policy": "YYMMDD acquisition-prefix groups are disjoint across splits",
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
        "selection": {
            "rule": "highest validation macro-F1, then balanced accuracy, then ROC-AUC",
            "candidates": candidate_results,
            "selected_model": selected_name,
            "selected_threshold": round(threshold, 6),
            "validation": selected_validation,
        },
        "test": {
            "protocol": {
                "model_and_threshold_selected_on": "validation",
                "selection_frozen_before_test_evaluation": True,
                "test_used_for_selection": False,
                "regeneration_note": (
                    "The report may be regenerated deterministically after code or provenance "
                    "updates; test metrics must never drive model, threshold or feature choices."
                ),
            },
            "metrics": test_metrics,
            "group_bootstrap_95_percent": bootstrap,
            "bootstrap_unit": "acquisition_prefix",
            "bootstrap_groups": int(len(np.unique(test_groups))),
            "bootstrap_iterations": int(config["bootstrap_iterations"]),
            "majority_baseline": majority_metrics,
            "by_cell_type": _slice_metrics(
                test_rows, test_labels, test_probabilities, threshold, "cell_type"
            ),
            "by_day_bucket": _slice_metrics(
                test_rows, test_labels, test_probabilities, threshold, "day_bucket"
            ),
        },
        "interpretability": {
            "top_features": _feature_ranking(selected_model, feature_names),
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
                "rows": len(test_rows),
            },
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "numpy": np.__version__,
            "pillow": PIL.__version__,
            "scikit_image": skimage.__version__,
            "scikit_learn": sklearn.__version__,
            "joblib": joblib.__version__,
        },
        "historical_context": config.get("historical_context", []),
        "warnings": [
            (
                "This model predicts the dataset's expert good/bad image-quality label; "
                "it does not infer toxicity or treatment efficacy."
            ),
            (
                "The acquisition prefix is only a date heuristic because chip, well, donor "
                "and experiment identifiers are unavailable."
            ),
            (
                "Historical MobileNetV3 results use the published split and are not directly "
                "comparable to this grouped test."
            ),
            (
                "Slice balanced accuracy, macro-F1 and ROC-AUC are null when a slice contains "
                "only one ground-truth class."
            ),
        ],
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
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    report = run(config_path.resolve())
    print(
        json.dumps(
            {
                "selected_model": report["selection"]["selected_model"],
                "validation": report["selection"]["validation"],
                "test": report["test"]["metrics"],
                "bootstrap": report["test"]["group_bootstrap_95_percent"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
