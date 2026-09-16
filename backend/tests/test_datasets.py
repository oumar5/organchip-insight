import hashlib
import zipfile

import pytest

from app.datasets import DatasetError, extract_resource, verify_resource


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
