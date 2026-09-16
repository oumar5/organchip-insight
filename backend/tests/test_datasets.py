import hashlib
import io
import zipfile

import pytest

from app.datasets import DatasetError, download_resource, extract_resource, verify_resource


def test_verify_resource_checks_size_and_digest(tmp_path) -> None:
    payload = b"reproducible microscopy data"
    path = tmp_path / "data.bin"
    path.write_bytes(payload)
    resource = {
        "id": "fixture",
        "path": "data.bin",
        "size_bytes": len(payload),
        "checksums": {"sha256": hashlib.sha256(payload).hexdigest()},
    }

    result = verify_resource(resource, tmp_path)

    assert result["status"] == "verified"
    assert result["checksums"]["sha256"] == resource["checksums"]["sha256"]


def test_safe_extraction_rejects_parent_traversal(tmp_path) -> None:
    archive_path = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.txt", "must not escape")
    resource = {
        "id": "unsafe",
        "path": "unsafe.zip",
        "extraction": {"type": "zip", "destination": "extracted"},
    }

    with pytest.raises(DatasetError, match="Unsafe path"):
        extract_resource(resource, tmp_path)

    assert not (tmp_path.parent / "outside.txt").exists()


def test_download_resource_resumes_partial_file(tmp_path, monkeypatch) -> None:
    payload = b"reproducible microscopy data"
    destination = tmp_path / "nested" / "fixture.bin"
    destination.parent.mkdir()
    partial = destination.with_name("fixture.bin.part")
    partial.write_bytes(payload[:10])

    class PartialResponse(io.BytesIO):
        status = 206
        headers = {"Content-Range": f"bytes 10-{len(payload) - 1}/{len(payload)}"}

        def getcode(self) -> int:
            return self.status

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None:
            self.close()

    def fake_urlopen(request, timeout):
        assert timeout == 120
        assert request.get_header("Range") == "bytes=10-"
        return PartialResponse(payload[10:])

    monkeypatch.setattr("app.datasets.urllib.request.urlopen", fake_urlopen)
    resource = {
        "id": "fixture",
        "url": "https://example.test/fixture.bin",
        "path": "nested/fixture.bin",
        "size_bytes": len(payload),
    }

    result = download_resource(resource, tmp_path)

    assert result == destination
    assert result.read_bytes() == payload
    assert not partial.exists()
