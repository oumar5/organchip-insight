from io import BytesIO

from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

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
    assert "Upload at least one image" in response.json()["detail"]


def test_upload_and_analyze_real_image() -> None:
    create_response = client.post(
        "/api/v1/experiments",
        json={"name": "Microscopy quality control"},
    )
    experiment_id = create_response.json()["id"]

    image_buffer = BytesIO()
    Image.new("L", (16, 16), color=128).save(image_buffer, format="PNG")
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
    assert result["analysis_version"] == "image-qc-baseline-0.1.0"
    assert result["metrics"]["mean_intensity"] > 0
