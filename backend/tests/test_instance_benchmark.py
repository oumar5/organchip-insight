from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.instance_benchmark import (
    instance_iou_matrix,
    load_instance_truth,
    object_metrics,
)


def test_instance_iou_matrix_and_object_metrics() -> None:
    truth = np.array(
        [
            [1, 1, 0, 2, 2],
            [1, 1, 0, 2, 2],
            [0, 0, 0, 0, 0],
        ]
    )
    prediction = np.array(
        [
            [7, 7, 0, 9, 0],
            [7, 7, 0, 9, 0],
            [0, 0, 0, 0, 11],
        ]
    )

    matrix = instance_iou_matrix(prediction, truth)
    metrics_50 = object_metrics(prediction, truth, iou_threshold=0.5)
    metrics_75 = object_metrics(prediction, truth, iou_threshold=0.75)

    assert matrix.shape == (2, 3)
    assert matrix[0, 0] == 1.0
    assert matrix[1, 1] == 0.5
    assert metrics_50["true_positive"] == 2
    assert metrics_50["false_positive"] == 1
    assert metrics_50["false_negative"] == 0
    assert metrics_50["f1"] == pytest.approx(0.8)
    assert metrics_75["true_positive"] == 1


def test_load_instance_truth_rejects_overlaps(tmp_path: Path) -> None:
    masks = tmp_path / "masks"
    masks.mkdir()
    first = np.zeros((4, 4), dtype=np.uint8)
    first[1:3, 1:3] = 255
    second = np.zeros((4, 4), dtype=np.uint8)
    second[2:4, 2:4] = 255
    Image.fromarray(first).save(masks / "a.png")
    Image.fromarray(second).save(masks / "b.png")

    with pytest.raises(ValueError, match="Overlapping"):
        load_instance_truth(masks, (4, 4))


def test_load_instance_truth_labels_each_mask(tmp_path: Path) -> None:
    masks = tmp_path / "masks"
    masks.mkdir()
    first = np.zeros((4, 4), dtype=np.uint8)
    first[0, 0] = 255
    second = np.zeros((4, 4), dtype=np.uint8)
    second[3, 3] = 255
    Image.fromarray(first).save(masks / "a.png")
    Image.fromarray(second).save(masks / "b.png")

    labels = load_instance_truth(masks, (4, 4))

    assert labels[0, 0] == 1
    assert labels[3, 3] == 2
    assert labels.max() == 2
