from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from app.ml.quality_classifier import (
    ExperimentalQualityAnalyzer,
    QualityModelBundle,
    _preprocess,
    verify_quality_model_bundle,
)
from app.ml.registry import EXPERIMENTAL_QUALITY_ENGINE
from training.ooc_cnn.preprocessing import force_grayscale_rgb, resize_and_pad


class FakeSession:
    def run(self, output_names, inputs):
        assert output_names == ["logits"]
        assert inputs["images"].shape == (1, 3, 448, 448)
        return [np.asarray([[0.0, np.log(3.0)]], dtype=np.float32)]


def test_product_preprocessing_matches_training_preprocessing() -> None:
    source = Image.new("RGB", (17, 9), color=(12, 80, 230))
    expected_image = resize_and_pad(force_grayscale_rgb(source), size=448)
    expected = np.asarray(expected_image, dtype=np.float32) / 255.0
    expected = (expected - np.asarray((0.485, 0.456, 0.406))) / np.asarray(
        (0.229, 0.224, 0.225)
    )
    expected = np.transpose(expected, (2, 0, 1))[None, ...].astype(np.float32)

    assert np.allclose(_preprocess(source), expected, atol=1e-6)


def test_experimental_classifier_always_abstains_and_rejects_unknown_modes(
    tmp_path: Path,
) -> None:
    grayscale = tmp_path / "field-l.png"
    palette = tmp_path / "field-p.png"
    Image.new("L", (24, 16), color=128).save(grayscale)
    Image.new("P", (24, 16), color=0).save(palette)
    analyzer = ExperimentalQualityAnalyzer(
        bundle=QualityModelBundle(model_path=tmp_path / "model.onnx"),
        session=FakeSession(),
        engine=EXPERIMENTAL_QUALITY_ENGINE.model_copy(update={"runnable": True}),
    )

    output = analyzer.analyze(
        [grayscale, palette],
        artifact_dir=tmp_path / "artifacts",
        artifact_url_prefix="/unused",
    )

    assert output.artifacts == []
    assert output.metrics == {
        "images_with_raw_score": 1.0,
        "images_outside_training_domain": 1.0,
    }
    scored, outside = output.image_results
    assert scored.analysis_type == "quality-classification"
    assert scored.source_acquisition_mode == "L"
    assert scored.probability_good_raw == pytest.approx(0.75)
    assert scored.review_required is True
    assert scored.interpretation == "review-required"
    assert outside.probability_good_raw is None
    assert outside.interpretation == "outside-training-domain"
    assert all(result.review_required is True for result in output.image_results)
    assert output.provenance["model_sha256"] == analyzer.bundle.model_sha256


def test_bundle_verification_fails_closed_on_unapproved_hashes(tmp_path: Path) -> None:
    (tmp_path / "model.onnx").write_bytes(b"not-the-authorized-model")
    (tmp_path / "preprocessing.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / "labels.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="SHA-256 inattendue"):
        verify_quality_model_bundle(tmp_path)
