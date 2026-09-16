"""Pure NumPy/scikit-learn metrics for OoC binary classification.

Class ``1`` is the positive ``good`` image-quality label and class ``0`` is the
negative ``bad`` label.  This module deliberately performs no file access so
validation and final-evaluation callers control which split is visible.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np
from numpy.typing import ArrayLike, NDArray
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

DEFAULT_THRESHOLDS = tuple(float(value) for value in np.linspace(0.05, 0.95, 181))
BOOTSTRAP_METRICS = (
    "accuracy",
    "balanced_accuracy",
    "precision_good",
    "recall_good",
    "f1_good",
    "macro_f1",
    "roc_auc",
    "pr_auc",
    "brier_score",
    "ece",
)


def _validate_binary_inputs(
    labels: ArrayLike, probabilities: ArrayLike
) -> tuple[NDArray[np.int64], NDArray[np.float64]]:
    label_array = np.asarray(labels)
    try:
        probability_array = np.asarray(probabilities, dtype=np.float64)
    except (TypeError, ValueError) as error:
        raise ValueError("Probabilities must be numeric") from error
    if label_array.ndim != 1 or probability_array.ndim != 1:
        raise ValueError("Labels and probabilities must be one-dimensional")
    if len(label_array) == 0:
        raise ValueError("Labels and probabilities cannot be empty")
    if len(label_array) != len(probability_array):
        raise ValueError("Labels and probabilities must have equal length")
    if not np.all(np.isin(label_array, (0, 1))):
        raise ValueError("Labels must contain only binary values 0 and 1")
    if not np.isfinite(probability_array).all():
        raise ValueError("Probabilities must be finite")
    if np.any((probability_array < 0.0) | (probability_array > 1.0)):
        raise ValueError("Probabilities must be between zero and one")
    return label_array.astype(np.int64, copy=False), probability_array


def _validate_threshold(threshold: float) -> float:
    if isinstance(threshold, (bool, np.bool_)):
        raise ValueError("Threshold must be a finite number between zero and one")
    try:
        value = float(threshold)
    except (TypeError, ValueError) as error:
        raise ValueError("Threshold must be a finite number between zero and one") from error
    if not np.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("Threshold must be a finite number between zero and one")
    return value


def _validate_ece_bins(ece_bins: int) -> int:
    if isinstance(ece_bins, (bool, np.bool_)) or not isinstance(ece_bins, (int, np.integer)):
        raise ValueError("ECE bin count must be a positive integer")
    if int(ece_bins) <= 0:
        raise ValueError("ECE bin count must be a positive integer")
    return int(ece_bins)


def _expected_calibration_error(
    labels: NDArray[np.int64], probabilities: NDArray[np.float64], bins: int
) -> float:
    bin_indices = np.minimum((probabilities * bins).astype(np.int64), bins - 1)
    error = 0.0
    for bin_index in range(bins):
        mask = bin_indices == bin_index
        count = int(mask.sum())
        if count == 0:
            continue
        confidence = float(probabilities[mask].mean())
        observed_rate = float(labels[mask].mean())
        error += count / len(labels) * abs(confidence - observed_rate)
    return float(error)


def binary_metrics(
    labels: ArrayLike,
    probabilities: ArrayLike,
    threshold: float,
    *,
    ece_bins: int = 10,
) -> dict[str, Any]:
    """Return JSON-compatible binary metrics at a fixed threshold.

    Discrimination metrics that require both target classes are ``None`` for a
    mono-class sample. Accuracy and probabilistic calibration metrics remain
    defined in that case.
    """

    label_array, probability_array = _validate_binary_inputs(labels, probabilities)
    threshold_value = _validate_threshold(threshold)
    bin_count = _validate_ece_bins(ece_bins)
    predictions = (probability_array >= threshold_value).astype(np.int64)
    bad_count = int(np.sum(label_array == 0))
    good_count = int(np.sum(label_array == 1))
    both_classes_present = bad_count > 0 and good_count > 0
    matrix = confusion_matrix(label_array, predictions, labels=[0, 1])
    true_bad, false_good, false_bad, true_good = (
        int(matrix[0, 0]),
        int(matrix[0, 1]),
        int(matrix[1, 0]),
        int(matrix[1, 1]),
    )

    conditional_metrics: dict[str, float | None]
    if both_classes_present:
        conditional_metrics = {
            "balanced_accuracy": float(balanced_accuracy_score(label_array, predictions)),
            "precision_good": float(
                precision_score(label_array, predictions, zero_division=0)
            ),
            "recall_good": float(recall_score(label_array, predictions, zero_division=0)),
            "f1_good": float(f1_score(label_array, predictions, zero_division=0)),
            "macro_f1": float(
                f1_score(label_array, predictions, average="macro", zero_division=0)
            ),
            "roc_auc": float(roc_auc_score(label_array, probability_array)),
            "pr_auc": float(average_precision_score(label_array, probability_array)),
        }
    else:
        conditional_metrics = {
            "balanced_accuracy": None,
            "precision_good": None,
            "recall_good": None,
            "f1_good": None,
            "macro_f1": None,
            "roc_auc": None,
            "pr_auc": None,
        }

    return {
        "support": int(len(label_array)),
        "class_counts": {"bad": bad_count, "good": good_count},
        "classes_present": [
            value for value, count in ((0, bad_count), (1, good_count)) if count > 0
        ],
        "both_classes_present": both_classes_present,
        "threshold": threshold_value,
        "positive_rate": float(label_array.mean()),
        "predicted_positive_rate": float(predictions.mean()),
        "confusion_matrix": matrix.tolist(),
        "confusion": {
            "true_bad": true_bad,
            "false_good": false_good,
            "false_bad": false_bad,
            "true_good": true_good,
        },
        "accuracy": float(accuracy_score(label_array, predictions)),
        **conditional_metrics,
        "brier_score": float(brier_score_loss(label_array, probability_array)),
        "ece": _expected_calibration_error(label_array, probability_array, bin_count),
        "ece_bins": bin_count,
        "ece_method": "equal_width",
        "pr_auc_method": "average_precision",
    }


def select_threshold(
    labels: ArrayLike,
    probabilities: ArrayLike,
    *,
    thresholds: Iterable[float] | None = None,
    ece_bins: int = 10,
) -> tuple[float, dict[str, Any]]:
    """Select a validation threshold by macro-F1 with deterministic tie-breaks."""

    label_array, probability_array = _validate_binary_inputs(labels, probabilities)
    if len(np.unique(label_array)) != 2:
        raise ValueError("Threshold selection requires both target classes")
    candidate_source = DEFAULT_THRESHOLDS if thresholds is None else thresholds
    candidate_values = sorted({_validate_threshold(value) for value in candidate_source})
    if not candidate_values:
        raise ValueError("Threshold selection requires at least one candidate")
    scored = [
        (
            threshold,
            binary_metrics(
                label_array,
                probability_array,
                threshold,
                ece_bins=ece_bins,
            ),
        )
        for threshold in candidate_values
    ]
    selected_threshold, selected_metrics = max(
        scored,
        key=lambda item: (
            item[1]["macro_f1"],
            item[1]["balanced_accuracy"],
            -abs(item[0] - 0.5),
            -item[0],
        ),
    )
    return selected_threshold, selected_metrics


def _validate_string_values(
    values: Sequence[str] | NDArray[np.str_], *, expected_length: int, label: str
) -> NDArray[np.object_]:
    array = np.asarray(values, dtype=object)
    if array.ndim != 1 or len(array) != expected_length:
        raise ValueError(f"{label} must be one-dimensional and match label count")
    if any(not isinstance(value, str) or not value for value in array):
        raise ValueError(f"{label} must contain non-empty strings")
    return array


def metrics_by_slice(
    labels: ArrayLike,
    probabilities: ArrayLike,
    attributes: Sequence[str] | NDArray[np.str_],
    threshold: float,
    *,
    ece_bins: int = 10,
) -> dict[str, dict[str, Any]]:
    """Compute fixed-threshold metrics for each sorted attribute value."""

    label_array, probability_array = _validate_binary_inputs(labels, probabilities)
    attribute_array = _validate_string_values(
        attributes, expected_length=len(label_array), label="Slice attributes"
    )
    output: dict[str, dict[str, Any]] = {}
    for value in sorted(set(attribute_array.tolist())):
        indices = np.flatnonzero(attribute_array == value)
        output[value] = binary_metrics(
            label_array[indices],
            probability_array[indices],
            threshold,
            ece_bins=ece_bins,
        )
    return output


def bootstrap_metrics_by_group(
    labels: ArrayLike,
    probabilities: ArrayLike,
    acquisition_prefixes: Sequence[str] | NDArray[np.str_],
    threshold: float,
    *,
    iterations: int,
    seed: int,
    confidence_level: float = 0.95,
    ece_bins: int = 10,
) -> dict[str, Any]:
    """Return percentile intervals from an acquisition-prefix cluster bootstrap."""

    label_array, probability_array = _validate_binary_inputs(labels, probabilities)
    group_array = _validate_string_values(
        acquisition_prefixes,
        expected_length=len(label_array),
        label="Acquisition prefixes",
    )
    _validate_threshold(threshold)
    bin_count = _validate_ece_bins(ece_bins)
    if isinstance(iterations, (bool, np.bool_)) or not isinstance(
        iterations, (int, np.integer)
    ):
        raise ValueError("Bootstrap iterations must be a positive integer")
    if int(iterations) <= 0:
        raise ValueError("Bootstrap iterations must be a positive integer")
    if isinstance(seed, (bool, np.bool_)) or not isinstance(seed, (int, np.integer)):
        raise ValueError("Bootstrap seed must be an integer")
    try:
        confidence = float(confidence_level)
    except (TypeError, ValueError) as error:
        raise ValueError("Confidence level must be between zero and one") from error
    if not np.isfinite(confidence) or not 0.0 < confidence < 1.0:
        raise ValueError("Confidence level must be between zero and one")

    unique_groups = np.asarray(sorted(set(group_array.tolist())), dtype=object)
    if len(unique_groups) < 2:
        raise ValueError("Group bootstrap requires at least two acquisition prefixes")
    group_indices = {
        group: np.flatnonzero(group_array == group) for group in unique_groups.tolist()
    }
    values: dict[str, list[float]] = {name: [] for name in BOOTSTRAP_METRICS}
    rng = np.random.default_rng(int(seed))
    for _iteration in range(int(iterations)):
        sampled_positions = rng.integers(0, len(unique_groups), size=len(unique_groups))
        indices = np.concatenate(
            [group_indices[unique_groups[position]] for position in sampled_positions]
        )
        result = binary_metrics(
            label_array[indices],
            probability_array[indices],
            threshold,
            ece_bins=bin_count,
        )
        for name in BOOTSTRAP_METRICS:
            value = result[name]
            if value is not None:
                values[name].append(float(value))

    tail_probability = (1.0 - confidence) / 2.0
    intervals: dict[str, dict[str, float | int | None]] = {}
    for name, metric_values in values.items():
        if metric_values:
            lower, upper = np.quantile(
                np.asarray(metric_values, dtype=np.float64),
                [tail_probability, 1.0 - tail_probability],
            )
            low: float | None = float(lower)
            high: float | None = float(upper)
        else:
            low = None
            high = None
        intervals[name] = {
            "low": low,
            "high": high,
            "valid_iterations": len(metric_values),
        }
    return {
        "unit": "acquisition_prefix",
        "groups": int(len(unique_groups)),
        "iterations": int(iterations),
        "seed": int(seed),
        "confidence_level": confidence,
        "intervals": intervals,
    }
