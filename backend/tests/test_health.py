import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ml import registry, runtime

client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["inference_ready"] is True


def test_health_reports_when_no_inference_engine_is_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(registry.ADAPTIVE_SEGMENTATION_ENGINE, "status", "experimental")

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["inference_ready"] is False


def test_health_fails_closed_for_an_inconsistent_runtime_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runtime,
        "REGISTERED_ENGINES",
        (*runtime.REGISTERED_ENGINES, registry.ADAPTIVE_SEGMENTATION_ENGINE),
    )

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json()["inference_ready"] is False
