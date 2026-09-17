#!/usr/bin/env python3
"""Fail when tracked release content contains private data or local artifacts."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BLOCKED_PREFIXES = (
    "artifacts/",
    "backend/data/",
    "data/cache/",
    "data/experiments/",
    "data/models/",
    "data/processed/",
    "data/raw/",
    "frontend/node_modules/",
    "frontend/playwright-report/",
    "frontend/test-results/",
    "organchip-kaggle-uploads-v2/",
    "reports/generated/",
)
BLOCKED_PARTS = {".mypy_cache", ".pytest_cache", ".ruff_cache", "__pycache__"}
BLOCKED_SUFFIXES = {".db", ".onnx", ".pt", ".pth", ".sqlite", ".sqlite3"}
SECRET_PATTERNS = {
    "AWS access key": re.compile(rb"AKIA[0-9A-Z]{16}"),
    "GitHub token": re.compile(rb"gh[pousr]_[A-Za-z0-9_]{20,}"),
    "private key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "personal absolute path": re.compile(rb"(?:/Users|/home)/[A-Za-z0-9._-]+/"),
    "Windows personal path": re.compile(rb"[A-Za-z]:\\Users\\[A-Za-z0-9._-]+\\"),
}
MAX_SCANNED_BYTES = 5 * 1024 * 1024


def tracked_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )
    return [Path(item.decode()) for item in completed.stdout.split(b"\0") if item]


def audit() -> list[str]:
    violations: list[str] = []
    for relative_path in tracked_files():
        posix_path = relative_path.as_posix()
        if posix_path.startswith(BLOCKED_PREFIXES):
            violations.append(f"local or private artifact is tracked: {posix_path}")
        if BLOCKED_PARTS.intersection(relative_path.parts):
            violations.append(f"cache is tracked: {posix_path}")
        if relative_path.name.startswith(".env") and relative_path.name != ".env.example":
            violations.append(f"environment file is tracked: {posix_path}")
        if relative_path.suffix.lower() in BLOCKED_SUFFIXES:
            violations.append(f"undistributable binary is tracked: {posix_path}")

        absolute_path = REPOSITORY_ROOT / relative_path
        if not absolute_path.is_file() or absolute_path.stat().st_size > MAX_SCANNED_BYTES:
            continue
        contents = absolute_path.read_bytes()
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(contents):
                violations.append(f"{label} found in tracked file: {posix_path}")
    return sorted(set(violations))


def main() -> None:
    violations = audit()
    print(
        json.dumps(
            {
                "status": "failed" if violations else "passed",
                "tracked_files": len(tracked_files()),
                "violations": violations,
            },
            ensure_ascii=False,
        )
    )
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
