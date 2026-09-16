"""Create deterministic, integrity-checked archives of CNN run artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from training.ooc_cnn.manifests import sha256_file

_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _archive_entry(name: str, content: bytes) -> tuple[zipfile.ZipInfo, bytes]:
    info = zipfile.ZipInfo(name, date_time=_ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o644) << 16
    return info, content


def _payload_files(run_directory: Path) -> list[Path]:
    files: list[Path] = []
    for path in sorted(run_directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Artifact run contains a symbolic link: {path}")
        if path.is_file():
            if path.relative_to(run_directory) == Path("artifact-manifest.json"):
                continue
            files.append(path)
    if not files:
        raise ValueError("Artifact run does not contain any files")
    return files


def create_artifact_archive(
    *,
    run_directory: Path,
    output_path: Path,
    archive_root: str | None = None,
) -> dict[str, Any]:
    """Archive one run without images, timestamps, or host-specific paths."""

    root = run_directory.resolve(strict=True)
    if not root.is_dir() or run_directory.is_symlink():
        raise ValueError(f"Artifact run directory is invalid: {run_directory}")

    output_parent = output_path.parent.resolve(strict=True)
    destination = output_parent / output_path.name
    if destination.suffix.casefold() != ".zip":
        raise ValueError("Artifact archive output must use the .zip suffix")
    try:
        destination.relative_to(root)
    except ValueError:
        pass
    else:
        raise ValueError("Artifact archive output must be outside the run directory")
    if destination.exists():
        raise FileExistsError(destination)

    root_name = archive_root or root.name
    if (
        not root_name
        or root_name in {".", ".."}
        or "/" in root_name
        or "\\" in root_name
    ):
        raise ValueError("Artifact archive root must be one safe path component")

    payload = _payload_files(root)
    records = [
        {
            "path": path.relative_to(root).as_posix(),
            "size_bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in payload
    ]
    manifest = {
        "schema_version": 1,
        "run_id": root.name,
        "archive_root": root_name,
        "file_count": len(records),
        "files": records,
    }
    manifest_bytes = (
        json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    )

    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{destination.stem}-",
            suffix=".tmp",
            dir=output_parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        with zipfile.ZipFile(
            temporary_path,
            mode="w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as archive:
            info, content = _archive_entry(
                f"{root_name}/artifact-manifest.json", manifest_bytes
            )
            archive.writestr(info, content, compresslevel=6)
            for path in payload:
                relative = path.relative_to(root).as_posix()
                info, content = _archive_entry(f"{root_name}/{relative}", path.read_bytes())
                archive.writestr(info, content, compresslevel=6)
        os.replace(temporary_path, destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)

    return {
        "archive": str(destination),
        "archive_root": root_name,
        "file_count": len(records),
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "sha256": sha256_file(destination),
        "size_bytes": destination.stat().st_size,
    }
