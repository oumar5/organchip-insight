import numpy as np
import pytest

from training.train_ooc_baseline import _metrics, _select_threshold


def test_metrics_report_two_class_support_and_scores() -> None:
    labels = np.asarray([0, 0, 1, 1], dtype=np.int64)
    probabilities = np.asarray([0.1, 0.7, 0.8, 0.9], dtype=np.float64)

    metrics = _metrics(labels, probabilities, 0.5)

    assert metrics["class_counts"] == {"bad": 2, "good": 2}
    assert metrics["both_classes_present"] is True
    assert metrics["confusion_matrix"] == [[1, 1], [0, 2]]
    assert metrics["balanced_accuracy"] == pytest.approx(0.75)
    assert metrics["macro_f1"] == pytest.approx(0.733333)
    assert metrics["roc_auc"] == pytest.approx(1.0)


@pytest.mark.parametrize(
    ("labels", "probabilities", "expected_counts"),
    [
        ([1, 1, 1], [0.8, 0.9, 0.7], {"bad": 0, "good": 3}),
        ([0, 0, 0], [0.1, 0.2, 0.3], {"bad": 3, "good": 0}),
    ],
)
def test_metrics_mark_single_class_slices_as_not_estimable(
    labels: list[int],
    probabilities: list[float],
    expected_counts: dict[str, int],
) -> None:
    metrics = _metrics(np.asarray(labels), np.asarray(probabilities), 0.5)

    assert metrics["class_counts"] == expected_counts
    assert metrics["both_classes_present"] is False
    assert metrics["balanced_accuracy"] is None
    assert metrics["macro_f1"] is None
    assert metrics["roc_auc"] is None


def test_threshold_selection_uses_validation_labels_only() -> None:
    labels = np.asarray([0, 0, 1, 1], dtype=np.int64)
    probabilities = np.asarray([0.1, 0.4, 0.6, 0.9], dtype=np.float64)

    threshold, metrics = _select_threshold(labels, probabilities)

    assert threshold == pytest.approx(0.5)
    assert metrics["macro_f1"] == 1.0


def test_threshold_selection_rejects_single_class_data() -> None:
    with pytest.raises(ValueError, match="both target classes"):
        _select_threshold(np.asarray([1, 1]), np.asarray([0.8, 0.9]))
