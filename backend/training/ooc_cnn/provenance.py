"""Small provenance helpers shared by the OoC CNN runtime and exporter."""

from __future__ import annotations

import importlib.metadata
import json
import os
import platform
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from training.ooc_cnn.manifests import relative_project_path, sha256_file


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def git_state(project_root: Path) -> dict[str, Any]:
    def run(*arguments: str) -> str | None:
        try:
            return subprocess.check_output(
                ["git", *arguments],
                cwd=project_root,
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return None

    commit = run("rev-parse", "HEAD")
    status = run("status", "--porcelain=v1", "--untracked-files=normal")
    return {
        "commit": commit,
        "available": commit is not None,
        "dirty": bool(status) if status is not None else None,
        "status": status.splitlines() if status else [],
    }


def package_versions(names: tuple[str, ...]) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def environment_snapshot(*, device: str | None = None) -> dict[str, Any]:
    return {
        "captured_at_utc": utc_now(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "device": device,
        "packages": package_versions(
            (
                "torch",
                "torchvision",
                "numpy",
                "Pillow",
                "scikit-learn",
                "matplotlib",
                "onnx",
                "onnxruntime",
            )
        ),
    }


def source_hashes(project_root: Path, paths: list[Path]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for path in sorted({item.resolve() for item in paths}):
        output.append(
            {
                "path": relative_project_path(project_root, path, field="source file"),
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return output


def write_json_atomic(path: Path, value: Any, *, overwrite: bool = True) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        if overwrite:
            temporary_path.replace(path)
        else:
            os.link(temporary_path, path)
            temporary_path.unlink()
    except BaseException:
        temporary_path.unlink(missing_ok=True)
        raise


def artifact_record(project_root: Path, path: Path) -> dict[str, Any]:
    return {
        "path": relative_project_path(project_root, path, field="artifact"),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
