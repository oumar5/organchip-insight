from io import BytesIO
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.api.routes import experiments
from app.main import app
from app.ml.runtime import ANALYZERS_BY_ENGINE_ID

client = TestClient(app)


def create() -> str:
    response = client.post("/api/v1/experiments", json={"name": "Import robustness"})
    assert response.status_code == 201
    return f"/api/v1/experiments/{response.json()['id']}"


def picture(value: int = 128, format: str = "PNG") -> bytes:
    buffer = BytesIO()
    Image.new("L", (64, 64), value).save(buffer, format=format)
    return buffer.getvalue()


def upload(url: str, payload: bytes, name: str = "field.png"):
    return client.post(url + "/images", files={"files": (name, payload)})


def test_duplicate_bytes_are_not_stored_twice_even_with_another_filename():
    url = create()
    first = upload(url, picture()).json()
    assert first["accepted_files"] == ["field.png"]
    second = upload(url, picture(), "renamed.png").json()
    assert second["duplicate_files"] == ["renamed.png"]
    assert second["accepted_files"] == []
    assert second["total_images"] == 1


def test_partial_upload_lists_reasons_and_keeps_valid_images():
    url = create()
    response = client.post(
        url + "/images",
        files=[
            ("files", ("valid.png", picture())),
            ("files", ("corrupt.png", b"not an image")),
            ("files", ("notes.txt", b"text")),
        ],
    )
    summary = response.json()
    assert summary["accepted_files"] == ["valid.png"]
    assert summary["rejected_files"] == ["corrupt.png", "notes.txt"]
    assert set(summary["rejection_reasons"]) == {"corrupt.png", "notes.txt"}
    assert summary["total_images"] == 1


def test_truncated_jpeg_rejected_during_import():
    response = upload(create(), picture(format="JPEG")[:-50], "truncated.jpg")
    assert response.status_code == 200
    assert response.json()["rejected_files"] == ["truncated.jpg"]
    assert response.json()["total_images"] == 0


def test_pixel_limit_and_decompression_error_leave_no_orphan(monkeypatch):
    url = create()
    with monkeypatch.context() as patch:
        patch.setattr(experiments.settings, "max_image_pixels", 100)
        response = upload(url, picture())
    assert response.json()["rejected_files"] == ["field.png"]
    with monkeypatch.context() as patch:
        patch.setattr(Image, "MAX_IMAGE_PIXELS", 100)
        response = upload(url, picture())
    assert response.json()["rejected_files"] == ["field.png"]
    assert response.json()["total_images"] == 0
    assert list(experiments._experiment_image_dir(UUID(url.rsplit("/", 1)[-1])).iterdir()) == []


def test_long_utf8_filename_is_accepted_without_filesystem_error():
    name = "é" * 200 + ".png"
    response = upload(create(), picture(), name)
    assert response.status_code == 200
    assert response.json()["accepted_files"] == [name]


@pytest.mark.parametrize("failure", [RuntimeError("internal"), ValueError("bad image")])
def test_failed_analysis_is_retryable_without_new_upload(monkeypatch, failure):
    url = create()
    upload(url, picture())
    analyzer = ANALYZERS_BY_ENGINE_ID["adaptive-segmentation-v1"]

    def fail(*args, **kwargs):
        raise failure

    with monkeypatch.context() as patch:
        patch.setattr(analyzer, "analyze", fail)
        response = client.post(url + "/analyze")
    assert response.status_code in (422, 500)
    state = client.get(url).json()
    assert state["status"] == "failed"
    assert state["image_count"] == 1
    assert client.get(url + "/results").status_code == 404
    assert client.post(url + "/analyze").status_code == 200
    assert client.get(url).json()["image_count"] == 1


def test_new_upload_invalidates_results_but_rejection_and_duplicate_do_not():
    url = create()
    upload(url, picture())
    assert client.post(url + "/analyze").status_code == 200
    upload(url, b"bad", "bad.png")
    upload(url, picture())
    assert client.get(url + "/results").status_code == 200
    upload(url, picture(129), "other.png")
    assert client.get(url + "/results").status_code == 404
    assert client.get(url).json()["status"] == "ready"


def test_in_flight_analysis_rejects_second_analysis_and_upload():
    url = create()
    upload(url, picture())
    identifier = UUID(url.rsplit("/", 1)[-1])
    assert experiments.repository.start_analysis(identifier)
    assert client.post(url + "/analyze").status_code == 409
    assert upload(url, picture(129), "other.png").status_code == 409
    assert client.get(url).json()["image_count"] == 1
    experiments.repository.update_status(identifier, "failed")


def test_file_size_limit_leaves_no_image(monkeypatch):
    url = create()
    monkeypatch.setattr(experiments.settings, "max_upload_mb", 1)
    response = upload(url, b"x" * (1024 * 1024 + 1))
    assert response.json()["total_images"] == 0
    assert "volumineux" in response.json()["rejection_reasons"]["field.png"]
