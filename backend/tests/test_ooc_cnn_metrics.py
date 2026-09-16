import numpy as np
import pytest

from training.ooc_cnn.metrics import (
    binary_metrics,
    bootstrap_metrics_by_group,
    metrics_by_slice,
    select_threshold,
)


def test_binary_metrics_reports_complete_two_class_scores() -> None:
    labels = np.asarray([0, 0, 1, 1], dtype=np.int64)
    probabilities = np.asarray([0.1, 0.7, 0.8, 0.9], dtype=np.float64)

    result = binary_metrics(labels, probabilities, 0.5, ece_bins=2)

    assert result["support"] == 4
    assert result["class_counts"] == {"bad": 2, "good": 2}
    assert result["classes_present"] == [0, 1]
    assert result["both_classes_present"] is True
    assert result["confusion_matrix"] == [[1, 1], [0, 2]]
    assert result["confusion"] == {
        "true_bad": 1,
        "false_good": 1,
        "false_bad": 0,
        "true_good": 2,
    }
    assert result["accuracy"] == pytest.approx(0.75)
    assert result["balanced_accuracy"] == pytest.approx(0.75)
    assert result["precision_good"] == pytest.approx(2 / 3)
    assert result["recall_good"] == pytest.approx(1.0)
    assert result["f1_good"] == pytest.approx(0.8)
    assert result["macro_f1"] == pytest.approx(11 / 15)
    assert result["roc_auc"] == pytest.approx(1.0)
    assert result["pr_auc"] == pytest.approx(1.0)
    assert result["brier_score"] == pytest.approx(0.1375)
    assert result["ece"] == pytest.approx(0.125)
    assert result["ece_method"] == "equal_width"
    assert result["pr_auc_method"] == "average_precision"


@pytest.mark.parametrize(
    ("labels", "probabilities", "expected_counts", "expected_confusion"),
    [
        ([1, 1, 1], [0.8, 0.4, 0.7], {"bad": 0, "good": 3}, [[0, 0], [1, 2]]),
        ([0, 0, 0], [0.1, 0.6, 0.3], {"bad": 3, "good": 0}, [[2, 1], [0, 0]]),
    ],
)
def test_binary_metrics_marks_discrimination_scores_null_for_mono_class(
    labels: list[int],
    probabilities: list[float],
    expected_counts: dict[str, int],
    expected_confusion: list[list[int]],
) -> None:
    result = binary_metrics(labels, probabilities, 0.5)

    assert result["class_counts"] == expected_counts
    assert result["both_classes_present"] is False
    assert result["confusion_matrix"] == expected_confusion
    for name in (
        "balanced_accuracy",
        "precision_good",
        "recall_good",
        "f1_good",
        "macro_f1",
        "roc_auc",
        "pr_auc",
    ):
        assert result[name] is None
    assert isinstance(result["accuracy"], float)
    assert isinstance(result["brier_score"], float)
    assert isinstance(result["ece"], float)


@pytest.mark.parametrize(
    ("labels", "probabilities", "message"),
    [
        ([], [], "cannot be empty"),
        ([0, 1], [0.2], "equal length"),
        ([0, 2], [0.2, 0.8], "binary values"),
        ([0, 1], [0.2, np.nan], "finite"),
        ([0, 1], [-0.1, 0.8], "between zero and one"),
        ([[0], [1]], [0.2, 0.8], "one-dimensional"),
    ],
)
def test_binary_metrics_rejects_invalid_inputs(
    labels: object, probabilities: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        binary_metrics(labels, probabilities, 0.5)


def test_threshold_selection_is_deterministic_under_exact_tie() -> None:
    labels = [0, 1]
    probabilities = [0.4, 0.6]

    first = select_threshold(labels, probabilities, thresholds=[0.55, 0.45])
    second = select_threshold(labels, probabilities, thresholds=[0.45, 0.55])

    assert first == second
    assert first[0] == pytest.approx(0.45)
    assert first[1]["macro_f1"] == pytest.approx(1.0)


def test_threshold_selection_rejects_mono_class_or_no_candidates() -> None:
    with pytest.raises(ValueError, match="both target classes"):
        select_threshold([1, 1], [0.8, 0.9])
    with pytest.raises(ValueError, match="at least one candidate"):
        select_threshold([0, 1], [0.2, 0.8], thresholds=[])


def test_metrics_by_slice_is_sorted_and_marks_mono_class_slice() -> None:
    result = metrics_by_slice(
        labels=[0, 1, 1, 1],
        probabilities=[0.2, 0.8, 0.9, 0.7],
        attributes=["HPMEC", "HPMEC", "CACO", "CACO"],
        threshold=0.5,
    )

    assert list(result) == ["CACO", "HPMEC"]
    assert result["CACO"]["class_counts"] == {"bad": 0, "good": 2}
    assert result["CACO"]["macro_f1"] is None
    assert result["HPMEC"]["macro_f1"] == pytest.approx(1.0)


def test_metrics_by_slice_rejects_misaligned_or_missing_attributes() -> None:
    with pytest.raises(ValueError, match="match label count"):
        metrics_by_slice([0, 1], [0.2, 0.8], ["A549"], 0.5)
    with pytest.raises(ValueError, match="non-empty strings"):
        metrics_by_slice([0, 1], [0.2, 0.8], ["A549", ""], 0.5)


def test_group_bootstrap_is_deterministic_and_reports_mono_class_draws() -> None:
    arguments = {
        "labels": [0, 0, 1, 1],
        "probabilities": [0.1, 0.2, 0.8, 0.9],
        "acquisition_prefixes": ["date-a", "date-a", "date-b", "date-b"],
        "threshold": 0.5,
        "iterations": 40,
        "seed": 17,
        "ece_bins": 5,
    }

    first = bootstrap_metrics_by_group(**arguments)
    second = bootstrap_metrics_by_group(**arguments)

    assert first == second
    assert first["unit"] == "acquisition_prefix"
    assert first["groups"] == 2
    assert first["iterations"] == 40
    assert first["intervals"]["accuracy"] == {
        "low": 1.0,
        "high": 1.0,
        "valid_iterations": 40,
    }
    roc_interval = first["intervals"]["roc_auc"]
    assert 0 < roc_interval["valid_iterations"] < 40
    assert roc_interval["low"] == pytest.approx(1.0)
    assert roc_interval["high"] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"acquisition_prefixes": ["only", "only", "only", "only"]}, "at least two"),
        ({"iterations": 0}, "positive integer"),
        ({"confidence_level": 1.0}, "between zero and one"),
    ],
)
def test_group_bootstrap_rejects_invalid_protocol(
    overrides: dict[str, object], message: str
) -> None:
    arguments: dict[str, object] = {
        "labels": [0, 0, 1, 1],
        "probabilities": [0.1, 0.2, 0.8, 0.9],
        "acquisition_prefixes": ["date-a", "date-a", "date-b", "date-b"],
        "threshold": 0.5,
        "iterations": 10,
        "seed": 17,
    }
    arguments.update(overrides)

    with pytest.raises(ValueError, match=message):
        bootstrap_metrics_by_group(**arguments)  # type: ignore[arg-type]
