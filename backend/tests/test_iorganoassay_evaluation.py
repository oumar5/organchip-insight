import numpy as np

from evaluation.evaluate_iorganoassay import centroid_error, mask_metrics, write_csv


def test_mask_metrics_match_identical_foreground() -> None:
    truth = np.zeros((8, 8), dtype=bool)
    truth[2:6, 2:6] = True

    metrics = mask_metrics(truth.copy(), truth)

    assert metrics["f1"] == 1.0
    assert metrics["iou"] == 1.0
    assert metrics["centroid_error"] == 0.0


def test_centroid_error_is_missing_when_a_mask_is_empty() -> None:
    empty = np.zeros((8, 8), dtype=bool)
    truth = empty.copy()
    truth[3:5, 3:5] = True

    assert centroid_error(empty, truth) is None


def test_write_csv_uses_lf_endings(tmp_path) -> None:
    output = tmp_path / "report.csv"

    write_csv([{"sample_id": "Ctrl_01", "f1": 0.8}], output)

    assert output.read_bytes() == b"sample_id,f1\nCtrl_01,0.8\n"
