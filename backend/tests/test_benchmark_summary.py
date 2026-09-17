import pytest

from evaluation.build_benchmark_summary import build_summary


def _foreground_report(benchmark_id: str, image_count: int, f1: float) -> dict:
    return {
        "benchmark_id": benchmark_id,
        "results": {
            "image_count": image_count,
            "macro": {"f1": f1, "iou": 0.5},
            "macro_bootstrap_95_percent": {"f1": [f1 - 0.1, f1 + 0.1]},
        },
        "performance": {
            "mean_inference_seconds_per_image": 2.0,
            "process_max_rss_mb": 300.0,
        },
    }


def _instance_report() -> dict:
    return {
        "benchmark_id": "bbbc038-stage1-subset-v1-micro-sam-vit-b-lm-apg",
        "results": {
            "objects": {
                threshold: {
                    "macro": {"f1": value},
                    "macro_bootstrap_95_percent": {"f1": [value - 0.1, value + 0.1]},
                }
                for threshold, value in (("0.5", 0.6), ("0.75", 0.4))
            },
            "count": {"median_absolute_percentage_error": 0.15},
        },
        "performance": {
            "mean_inference_seconds_per_image": 40.0,
            "process_max_rss_mb": 8800.0,
        },
    }


def test_build_summary_preserves_report_metrics() -> None:
    summary = build_summary(
        {
            "bbbc019_adaptive": _foreground_report(
                "bbbc019-microfluidic-adaptive-segmentation-v1", 13, 0.42
            ),
            "bbbc019_micro_sam": _foreground_report(
                "bbbc019-microfluidic-micro-sam-vit-b-lm-apg", 13, 0.81
            ),
            "bbbc038_micro_sam": _instance_report(),
        },
        [{"path": "report.json", "sha256": "a" * 64}],
    )

    assert summary["sections"][0]["rows"][0]["metrics"][0]["value"] == 0.42
    assert summary["sections"][0]["rows"][1]["metrics"][0]["value"] == 0.81
    assert summary["sections"][1]["rows"][0]["metrics"][2]["value"] == 0.15


def test_build_summary_rejects_mismatched_bbbc019_samples() -> None:
    with pytest.raises(ValueError, match="same number"):
        build_summary(
            {
                "bbbc019_adaptive": _foreground_report(
                    "bbbc019-microfluidic-adaptive-segmentation-v1", 13, 0.42
                ),
                "bbbc019_micro_sam": _foreground_report(
                    "bbbc019-microfluidic-micro-sam-vit-b-lm-apg", 12, 0.81
                ),
                "bbbc038_micro_sam": _instance_report(),
            },
            [],
        )
