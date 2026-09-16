import json

import numpy as np
from PIL import Image

from app.benchmark import evaluate_config, foreground_metrics


def test_foreground_metrics_from_known_confusion_matrix() -> None:
    prediction = np.array([[True, True], [False, False]])
    truth = np.array([[True, False], [True, False]])

    metrics = foreground_metrics(prediction, truth)

    assert metrics["true_positive"] == 1
    assert metrics["false_positive"] == 1
    assert metrics["false_negative"] == 1
    assert metrics["true_negative"] == 1
    assert metrics["f1"] == 0.5
    assert metrics["iou"] == 1 / 3


def test_evaluate_config_runs_production_segmentation(tmp_path) -> None:
    images_dir = tmp_path / "images"
    masks_dir = tmp_path / "masks"
    images_dir.mkdir()
    masks_dir.mkdir()
    image = np.zeros((64, 64), dtype=np.uint8)
    image[20:40, 22:42] = 255
    truth = np.zeros((64, 64), dtype=np.uint8)
    truth[20:40, 22:42] = 255
    Image.fromarray(image).save(images_dir / "field.tif")
    Image.fromarray(truth).save(masks_dir / "field_manual.png")
    config = {
        "schema_version": 1,
        "benchmark_id": "synthetic-test",
        "dataset": {"id": "synthetic"},
        "engine": "adaptive-segmentation-v1",
        "images_dir": "images",
        "masks_dir": "masks",
        "image_glob": "*.tif",
        "mask_template": "{stem}_manual.png",
        "bootstrap_iterations": 100,
        "seed": 7,
        "output_json": "reports/result.json",
        "output_csv": "reports/result.csv",
    }
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")

    report = evaluate_config(config_path, tmp_path)

    assert report["results"]["image_count"] == 1
    assert report["results"]["macro"]["f1"] == 1.0
    assert (tmp_path / "reports/result.json").is_file()
    assert (tmp_path / "reports/result.csv").is_file()
