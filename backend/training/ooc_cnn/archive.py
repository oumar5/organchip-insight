"""Create deterministic, integrity-checked archives of CNN run artifacts."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from training.ooc_cnn.manifests import sha256_file, validate_sha256

_ZIP_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
_REPORT_NAMES = ("validation-report.json", "final-test-report.json")


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


def _load_run_report(run_directory: Path) -> tuple[Path, dict[str, Any]]:
    candidates = [
        run_directory / name
        for name in _REPORT_NAMES
        if (run_directory / name).is_file()
    ]
    if len(candidates) != 1:
        raise ValueError(
            "Artifact run must contain exactly one validation or final-test report"
        )
    report_path = candidates[0]
    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("Artifact run report is not valid JSON") from error
    if not isinstance(report, dict) or report.get("schema_version") != 1:
        raise ValueError("Artifact run report must use schema_version 1")
    run_id = report.get("run_id")
    if not isinstance(run_id, str) or not _RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("Artifact run report contains an invalid run_id")
    if report.get("mode") not in {"smoke", "validation", "final-eval"}:
        raise ValueError("Artifact run report contains an invalid mode")
    experiment_id = report.get("experiment_id")
    config = report.get("config")
    if not isinstance(experiment_id, str) or not experiment_id:
        raise ValueError("Artifact run report contains an invalid experiment_id")
    if (
        not isinstance(config, dict)
        or not isinstance(config.get("path"), str)
        or not isinstance(config.get("sha256"), str)
    ):
        raise ValueError("Artifact run report config provenance is incomplete")
    validate_sha256(config["sha256"], "artifact run config sha256")
    return report_path, report


def create_artifact_archive(
    *,
    run_directory: Path,
    output_path: Path,
    source_bundle_sha256: str,
    source_commit: str,
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

    report_path, report = _load_run_report(root)
    run_id = report["run_id"]
    source_bundle_sha256 = validate_sha256(
        source_bundle_sha256, "artifact source bundle sha256"
    )
    if not _COMMIT_PATTERN.fullmatch(source_commit):
        raise ValueError("Artifact source commit must be a full hexadecimal Git commit")

    root_name = archive_root or run_id
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
        "schema_version": 2,
        "run_id": run_id,
        "archive_root": root_name,
        "file_count": len(records),
        "provenance": {
            "experiment_id": report["experiment_id"],
            "mode": report["mode"],
            "source_bundle_sha256": source_bundle_sha256,
            "source_commit": source_commit,
            "config": report["config"],
            "run_report": {
                "path": report_path.relative_to(root).as_posix(),
                "sha256": sha256_file(report_path),
            },
        },
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
