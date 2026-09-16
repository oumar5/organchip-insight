from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import urllib.error
import urllib.request
import zipfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any


class DatasetError(RuntimeError):
    """Raised when a dataset cannot be acquired or verified safely."""


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DatasetError(f"Cannot read dataset manifest {path}: {error}") from error

    resources = manifest.get("resources")
    if manifest.get("schema_version") != 1 or not isinstance(resources, list):
        raise DatasetError("Dataset manifest must use schema_version 1 and contain resources")

    identifiers = [resource.get("id") for resource in resources]
    has_missing_id = any(not identifier for identifier in identifiers)
    has_duplicate_id = len(set(identifiers)) != len(identifiers)
    if has_missing_id or has_duplicate_id:
        raise DatasetError("Every resource must have a unique non-empty id")
    return manifest


def selected_resources(
    manifest: dict[str, Any],
    resource_ids: Iterable[str] | None,
) -> list[dict[str, Any]]:
    resources = manifest["resources"]
    if not resource_ids:
        return [resource for resource in resources if resource.get("enabled_by_default", False)]

    requested = list(resource_ids)
    by_id = {resource["id"]: resource for resource in resources}
    missing = sorted(set(requested) - set(by_id))
    if missing:
        raise DatasetError(f"Unknown resource id(s): {', '.join(missing)}")
    return [by_id[identifier] for identifier in requested]


def calculate_checksums(path: Path, algorithms: Iterable[str]) -> dict[str, str]:
    digests: dict[str, Any] = {}
    for algorithm in algorithms:
        try:
            digests[algorithm] = hashlib.new(algorithm)
        except ValueError as error:
            raise DatasetError(f"Unsupported checksum algorithm: {algorithm}") from error

    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            for digest in digests.values():
                digest.update(chunk)
    return {name: digest.hexdigest() for name, digest in digests.items()}


def verify_resource(resource: dict[str, Any], project_root: Path) -> dict[str, Any]:
    path = project_root / resource["path"]
    if not path.is_file():
        raise DatasetError(f"Missing resource {resource['id']}: {path}")

    actual_size = path.stat().st_size
    expected_size = resource.get("size_bytes")
    if expected_size is not None and actual_size != expected_size:
        raise DatasetError(
            f"Size mismatch for {resource['id']}: expected {expected_size}, got {actual_size}"
        )

    expected_checksums = resource.get("checksums", {})
    actual_checksums = calculate_checksums(path, expected_checksums)
    for algorithm, expected in expected_checksums.items():
        if actual_checksums[algorithm].lower() != expected.lower():
            raise DatasetError(
                f"{algorithm} mismatch for {resource['id']}: "
                f"expected {expected}, got {actual_checksums[algorithm]}"
            )

    return {
        "id": resource["id"],
        "path": str(path.relative_to(project_root)),
        "size_bytes": actual_size,
        "checksums": actual_checksums,
        "status": "verified",
    }


def download_resource(resource: dict[str, Any], project_root: Path) -> Path:
    destination = project_root / resource["path"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f"{destination.name}.part")
    request = urllib.request.Request(
        resource["url"],
        headers={"User-Agent": "OrganChip-Insight/0.2 dataset acquisition"},
    )

    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            with temporary.open("wb") as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)
        os.replace(temporary, destination)
    except (OSError, urllib.error.URLError) as error:
        temporary.unlink(missing_ok=True)
        raise DatasetError(f"Download failed for {resource['id']}: {error}") from error
    return destination


def _safe_zip_members(archive: zipfile.ZipFile, destination: Path) -> list[zipfile.ZipInfo]:
    destination = destination.resolve()
    safe_members: list[zipfile.ZipInfo] = []
    for member in archive.infolist():
        member_path = Path(member.filename)
        if member_path.is_absolute() or ".." in member_path.parts:
            raise DatasetError(f"Unsafe path in archive: {member.filename}")

        mode = member.external_attr >> 16
        if stat.S_ISLNK(mode):
            raise DatasetError(f"Symbolic links are not allowed in archives: {member.filename}")

        target = (destination / member_path).resolve()
        if not target.is_relative_to(destination):
            raise DatasetError(f"Archive member escapes destination: {member.filename}")

        if "__MACOSX" in member_path.parts or member_path.name.lower() == "desktop.ini":
            continue
        safe_members.append(member)
    return safe_members


def extract_resource(resource: dict[str, Any], project_root: Path) -> dict[str, Any] | None:
    extraction = resource.get("extraction")
    if not extraction:
        return None
    if extraction.get("type") != "zip":
        raise DatasetError(f"Unsupported archive type for {resource['id']}")

    archive_path = project_root / resource["path"]
    destination = project_root / extraction["destination"]
    destination.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(archive_path) as archive:
            members = _safe_zip_members(archive, destination)
            archive.extractall(destination, members=members)
    except (OSError, zipfile.BadZipFile) as error:
        raise DatasetError(f"Cannot extract {resource['id']}: {error}") from error

    return {
        "id": resource["id"],
        "destination": str(destination.relative_to(project_root)),
        "files_extracted": sum(not member.is_dir() for member in members),
        "status": "extracted",
    }
