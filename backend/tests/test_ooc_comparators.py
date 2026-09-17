from pathlib import Path

import numpy as np
import pytest

from training.evaluate_ooc_comparators import (
    _categorical_probabilities,
    _evaluation,
    _fixed_categorical_comparator,
    _load_manifest,
)


def test_manifest_refuses_any_test_row(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "path,grouped_split\ntrain.png,train\ntest.png,test\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="train and validation only"):
        _load_manifest(manifest)


def test_categorical_comparator_is_fit_on_train_only() -> None:
    train = [
        {"mode_resolution": "L/10x10", "target_index": "0"},
        {"mode_resolution": "L/10x10", "target_index": "0"},
        {"mode_resolution": "RGB/8x8", "target_index": "1"},
        {"mode_resolution": "RGB/8x8", "target_index": "1"},
    ]
    validation = [
        {"mode_resolution": "L/10x10"},
        {"mode_resolution": "RGB/8x8"},
        {"mode_resolution": "RGBA/4x4"},
    ]

    probabilities, details = _categorical_probabilities(
        train, validation, field="mode_resolution"
    )

    assert probabilities == pytest.approx([0.25, 0.75, 0.5])
    assert details["unseen_validation_categories"] == ["RGBA/4x4"]
    assert details["global_train_probability_good"] == 0.5
    assert details["fixed_threshold"] == 0.5


def test_evaluation_reports_mode_slices() -> None:
    rows = [
        {"mode": "L", "resolution": "10x10"},
        {"mode": "L", "resolution": "10x10"},
        {"mode": "RGB", "resolution": "8x8"},
        {"mode": "RGB", "resolution": "8x8"},
    ]
    labels = np.asarray([0, 1, 0, 1], dtype=np.int64)
    probabilities = np.asarray([0.1, 0.9, 0.8, 0.7], dtype=np.float64)

    evaluation = _evaluation(rows, labels, probabilities, 0.5)

    assert evaluation["global"]["balanced_accuracy"] == pytest.approx(0.75)
    assert evaluation["by_mode"]["L"]["balanced_accuracy"] == pytest.approx(1.0)
    assert evaluation["by_mode"]["RGB"]["balanced_accuracy"] == pytest.approx(0.5)


def test_fixed_metadata_comparator_keeps_train_fit_and_threshold() -> None:
    train = [
        {
            "mode_day_bucket": "L/0-1_days",
            "target_index": "0",
        },
        {
            "mode_day_bucket": "L/0-1_days",
            "target_index": "0",
        },
        {
            "mode_day_bucket": "RGB/0-1_days",
            "target_index": "1",
        },
        {
            "mode_day_bucket": "RGB/0-1_days",
            "target_index": "1",
        },
    ]
    validation = [
        {
            "mode_day_bucket": "L/0-1_days",
            "mode": "L",
            "resolution": "10x10",
        },
        {
            "mode_day_bucket": "RGB/0-1_days",
            "mode": "RGB",
            "resolution": "8x8",
        },
    ]
    labels = np.asarray([0, 1], dtype=np.int64)

    probabilities, report = _fixed_categorical_comparator(
        train,
        validation,
        labels,
        field="mode_day_bucket",
    )

    assert probabilities == pytest.approx([0.25, 0.75])
    assert report["fit_split"] == "train"
    assert report["threshold"] == 0.5
    assert report["threshold_selection"] == "fixed before validation evaluation"
    assert report["validation"]["global"]["balanced_accuracy"] == pytest.approx(1.0)
