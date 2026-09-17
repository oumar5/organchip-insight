from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from app.main import app
from app.ml import registry, runtime
from app.ml.pipeline import PipelineOutput
from app.schemas import QualityImageAnalysis

client = TestClient(app)


def test_create_and_retrieve_experiment() -> None:
    payload = {
        "name": "Drug response pilot",
        "description": "Control versus treatment microscopy set",
        "control_label": "DMSO",
        "treatment_label": "Compound A",
    }

    create_response = client.post("/api/v1/experiments", json=payload)
    assert create_response.status_code == 201
    experiment = create_response.json()
    assert experiment["name"] == payload["name"]
    assert experiment["status"] == "draft"

    get_response = client.get(f"/api/v1/experiments/{experiment['id']}")
    assert get_response.status_code == 200
    assert get_response.json()["control_label"] == "DMSO"


def test_analysis_requires_images() -> None:
    create_response = client.post(
        "/api/v1/experiments",
        json={"name": "Empty experiment"},
    )
    experiment_id = create_response.json()["id"]

    response = client.post(f"/api/v1/experiments/{experiment_id}/analyze")

    assert response.status_code == 409
    assert "Importez au moins une image" in response.json()["detail"]


def test_upload_and_analyze_real_image() -> None:
    create_response = client.post(
        "/api/v1/experiments",
        json={"name": "Microscopy quality control"},
    )
    experiment_id = create_response.json()["id"]

    image_buffer = BytesIO()
    image = Image.new("L", (96, 96), color=8)
    drawing = ImageDraw.Draw(image)
    drawing.ellipse((12, 12, 36, 36), fill=230)
    drawing.ellipse((55, 48, 84, 77), fill=210)
    image.save(image_buffer, format="PNG")
    upload_response = client.post(
        f"/api/v1/experiments/{experiment_id}/images",
        files={"files": ("cell-field.png", image_buffer.getvalue(), "image/png")},
    )

    assert upload_response.status_code == 200
    assert upload_response.json()["total_images"] == 1

    analysis_response = client.post(f"/api/v1/experiments/{experiment_id}/analyze")
    assert analysis_response.status_code == 200
    result = analysis_response.json()
    assert result["image_count"] == 1
    assert result["analysis_version"] == "adaptive-segmentation-1.1.0"
    assert result["engine"]["kind"] == "zero-training"
    assert result["metrics"]["object_count_total"] == 2
    assert result["metrics"]["mean_intensity"] > 0
    assert len(result["artifacts"]) == 1

    overlay_response = client.get(result["artifacts"][0]["url"])
    assert overlay_response.status_code == 200
    assert overlay_response.headers["content-type"] == "image/png"

    json_export = client.get(
        f"/api/v1/experiments/{experiment_id}/exports/results.json"
    )
    assert json_export.status_code == 200
    assert json_export.headers["content-disposition"].endswith('results.json"')
    assert json_export.json()["task"] == "segmentation"

    csv_export = client.get(
        f"/api/v1/experiments/{experiment_id}/exports/results.csv"
    )
    assert csv_export.status_code == 200
    assert csv_export.headers["content-disposition"].endswith('image-results.csv"')
    assert "object_count" in csv_export.text.splitlines()[0]


def test_upload_rejects_invalid_image() -> None:
    create_response = client.post(
        "/api/v1/experiments",
        json={"name": "Invalid upload"},
    )
    experiment_id = create_response.json()["id"]
    response = client.post(
        f"/api/v1/experiments/{experiment_id}/images",
        files={"files": ("not-an-image.png", b"invalid", "image/png")},
    )

    assert response.status_code == 200
    assert response.json()["accepted_files"] == []
    assert response.json()["rejected_files"] == ["not-an-image.png"]


def test_inference_engine_registry_is_transparent() -> None:
    response = client.get("/api/v1/inference/engines")

    assert response.status_code == 200
    engines = response.json()
    engine_statuses = {engine["id"]: engine["status"] for engine in engines}
    assert engine_statuses == {
        "adaptive-segmentation-v1": "available",
        "ooc-quality-cnn-campaign-v2-gray448": "experimental",
        "micro-sam-pretrained": "experimental",
        "cellpose-pretrained": "license-review",
    }
    assert all(engine["limitations"] for engine in engines)
    runnable = {engine["id"]: engine["runnable"] for engine in engines}
    assert runnable["adaptive-segmentation-v1"] is True
    assert runnable["ooc-quality-cnn-campaign-v2-gray448"] is (
        "ooc-quality-cnn-campaign-v2-gray448" in runtime.ANALYZERS_BY_ENGINE_ID
    )
    micro_sam = next(engine for engine in engines if engine["id"] == "micro-sam-pretrained")
    assert any("deux des trois critères" in item for item in micro_sam["limitations"])
    assert any("images OoC" in item for item in micro_sam["limitations"])


def test_unavailable_inference_engines_are_rejected() -> None:
    create_response = client.post(
        "/api/v1/experiments",
        json={"name": "Unavailable engine guard"},
    )
    experiment_id = create_response.json()["id"]

    image_buffer = BytesIO()
    Image.new("L", (32, 32), color=128).save(image_buffer, format="PNG")
    upload_response = client.post(
        f"/api/v1/experiments/{experiment_id}/images",
        files={"files": ("field.png", image_buffer.getvalue(), "image/png")},
    )
    assert upload_response.status_code == 200

    for engine_id in ("micro-sam-pretrained", "cellpose-pretrained"):
        response = client.post(
            f"/api/v1/experiments/{experiment_id}/analyze",
            params={"engine_id": engine_id},
        )
        assert response.status_code == 422
        assert "is not available" in response.json()["detail"]


def test_experimental_quality_api_preserves_abstention_and_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeQualityAnalyzer:
        version = "quality-fixture-1"
        engine = registry.EXPERIMENTAL_QUALITY_ENGINE.model_copy(update={"runnable": True})

        def analyze(self, image_paths, artifact_dir, artifact_url_prefix):
            assert len(image_paths) == 1
            return PipelineOutput(
                metrics={"images_with_raw_score": 1.0},
                image_results=[
                    QualityImageAnalysis(
                        filename=image_paths[0].name,
                        source_acquisition_mode="L",
                        probability_good_raw=0.75,
                        interpretation="review-required",
                    )
                ],
                artifacts=[],
                warnings=["À vérifier"],
                provenance={"model_sha256": "a" * 64},
            )

    monkeypatch.setitem(
        runtime.ANALYZERS_BY_ENGINE_ID,
        registry.EXPERIMENTAL_QUALITY_ENGINE.id,
        FakeQualityAnalyzer(),
    )
    created = client.post("/api/v1/experiments", json={"name": "Quality demo"}).json()
    image_buffer = BytesIO()
    Image.new("L", (32, 32), color=128).save(image_buffer, format="PNG")
    upload_response = client.post(
        f"/api/v1/experiments/{created['id']}/images",
        files={"files": ("field.png", image_buffer.getvalue(), "image/png")},
    )
    assert upload_response.status_code == 200

    response = client.post(
        f"/api/v1/experiments/{created['id']}/analyze",
        params={"engine_id": registry.EXPERIMENTAL_QUALITY_ENGINE.id},
    )

    assert response.status_code == 200
    result = response.json()
    assert result["task"] == "quality-classification"
    assert result["engine"]["status"] == "experimental"
    assert result["engine"]["runnable"] is True
    assert result["artifacts"] == []
    assert result["provenance"]["model_sha256"] == "a" * 64
    assert result["image_results"][0] == {
        "analysis_type": "quality-classification",
        "filename": result["image_results"][0]["filename"],
        "source_acquisition_mode": "L",
        "probability_good_raw": 0.75,
        "review_required": True,
        "interpretation": "review-required",
    }


def test_registry_fails_closed_when_status_has_no_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(registry.MICRO_SAM_ENGINE, "status", "available")

    with pytest.raises(RuntimeError, match="mapping is inconsistent"):
        runtime.list_inference_engines()


def test_registry_can_report_no_runnable_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    adaptive_analyzer = runtime.ANALYZERS_BY_ENGINE_ID[
        registry.ADAPTIVE_SEGMENTATION_ENGINE.id
    ]
    monkeypatch.setattr(
        runtime,
        "ANALYZERS_BY_ENGINE_ID",
        {registry.ADAPTIVE_SEGMENTATION_ENGINE.id: adaptive_analyzer},
    )
    monkeypatch.setattr(registry.ADAPTIVE_SEGMENTATION_ENGINE, "runnable", False)

    assert not any(engine.runnable for engine in runtime.list_inference_engines())
    with pytest.raises(ValueError, match="is not available"):
        runtime.get_available_runtime(registry.ADAPTIVE_SEGMENTATION_ENGINE.id)


def test_runtime_dispatch_preserves_engine_provenance() -> None:
    engine, analyzer = runtime.get_available_runtime(registry.ADAPTIVE_SEGMENTATION_ENGINE.id)

    assert analyzer.engine is engine
    assert analyzer.engine.id == registry.ADAPTIVE_SEGMENTATION_ENGINE.id


def test_runtime_rejects_duplicate_registry_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        runtime,
        "REGISTERED_ENGINES",
        (*runtime.REGISTERED_ENGINES, registry.ADAPTIVE_SEGMENTATION_ENGINE),
    )

    with pytest.raises(RuntimeError, match=r"duplicates=\['adaptive-segmentation-v1'\]"):
        runtime.list_inference_engines()


def test_runtime_rejects_forged_engine_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    analyzer = runtime.ANALYZERS_BY_ENGINE_ID[registry.ADAPTIVE_SEGMENTATION_ENGINE.id]
    forged_engine = registry.ADAPTIVE_SEGMENTATION_ENGINE.model_copy(
        update={"name": "Métadonnées divergentes"}
    )
    monkeypatch.setattr(analyzer, "engine", forged_engine)

    with pytest.raises(RuntimeError, match=r"mismatched=\['adaptive-segmentation-v1'\]"):
        runtime.list_inference_engines()
