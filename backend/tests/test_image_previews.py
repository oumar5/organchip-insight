from io import BytesIO

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


def _experiment() -> str:
    response = client.post("/api/v1/experiments", json={"name": "Galerie"})
    assert response.status_code == 201
    return response.json()["id"]


def _upload(experiment_id: str, name: str, payload: bytes) -> dict:
    response = client.post(
        f"/api/v1/experiments/{experiment_id}/images", files={"files": (name, payload)}
    )
    assert response.status_code == 200
    return response.json()


def _png(value: int = 120) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (48, 32), (value, value // 2, 40)).save(buffer, format="PNG")
    return buffer.getvalue()


def _tiff16() -> bytes:
    pixels = np.full((40, 60), 400, dtype=np.uint16)
    pixels[10:30, 20:40] = 3000
    buffer = BytesIO()
    Image.fromarray(pixels).save(buffer, format="TIFF")
    return buffer.getvalue()


def test_lists_stored_images_with_display_names_and_preview_urls() -> None:
    experiment_id = _experiment()
    assert client.get(f"/api/v1/experiments/{experiment_id}/images").json() == []
    _upload(experiment_id, "champ-a.png", _png())
    _upload(experiment_id, "champ-b.tif", _tiff16())

    records = client.get(f"/api/v1/experiments/{experiment_id}/images").json()
    assert sorted(record["display_name"] for record in records) == ["champ-a.png", "champ-b.tif"]
    for record in records:
        assert record["filename"].endswith(record["display_name"])
        assert record["size_bytes"] > 0
        assert record["preview_url"].endswith(f"/previews/{record['filename']}")


def test_preview_renders_16_bit_tiff_as_visible_png() -> None:
    experiment_id = _experiment()
    _upload(experiment_id, "champ.tif", _tiff16())
    record = client.get(f"/api/v1/experiments/{experiment_id}/images").json()[0]

    response = client.get(record["preview_url"])
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    preview = Image.open(BytesIO(response.content))
    assert preview.mode == "L"
    values = np.asarray(preview)
    assert values.min() == 0 and values.max() == 255

    cached = client.get(record["preview_url"])
    assert cached.status_code == 200 and cached.content == response.content


def test_preview_rejects_traversal_and_unknown_images() -> None:
    experiment_id = _experiment()
    base = f"/api/v1/experiments/{experiment_id}/previews"
    assert client.get(f"{base}/..%2Fsecret.png").status_code in (400, 404)
    assert client.get(f"{base}/missing.png").status_code == 404
    assert client.get(f"{base}/notes.txt").status_code == 400
