#!/usr/bin/env python3
"""Build or verify the checksum inventory for competition deliverables."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_PATH = REPOSITORY_ROOT / "docs/release/release-checksums.sha256"
WEIGHT_SUFFIXES = {".onnx", ".pt", ".pth"}


def tracked_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )
    return [Path(item.decode()) for item in completed.stdout.split(b"\0") if item]


def is_deliverable(path: Path) -> bool:
    posix_path = path.as_posix()
    return (
        (posix_path.startswith("reports/") and path.suffix in {".csv", ".json"})
        or (posix_path.startswith("data/manifests/") and path.suffix == ".json")
        or (posix_path.startswith("notebooks/") and path.suffix == ".ipynb")
        or posix_path == "frontend/public/benchmark-summary.json"
        or (
            posix_path.startswith("docs/release/")
            and path.suffix == ".md"
        )
        or posix_path.startswith("docs/submission/")
        or (posix_path.startswith("output/pdf/") and path.suffix == ".pdf")
        or (
            posix_path.startswith("output/video/")
            and path.suffix in {".mp4", ".srt"}
        )
        or path.suffix.lower() in WEIGHT_SUFFIXES
    )


def checksum_inventory() -> str:
    lines = []
    for relative_path in sorted(path for path in tracked_files() if is_deliverable(path)):
        digest = hashlib.sha256((REPOSITORY_ROOT / relative_path).read_bytes()).hexdigest()
        lines.append(f"{digest}  {relative_path.as_posix()}")
    if not lines:
        raise RuntimeError("No tracked release deliverables were found")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    expected = checksum_inventory()
    if arguments.check:
        if not OUTPUT_PATH.is_file() or OUTPUT_PATH.read_text() != expected:
            raise SystemExit(
                "Release checksums are stale; run `make release-checksums` and review the diff."
            )
        status = "verified"
    else:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(expected)
        status = "written"
    print(
        json.dumps(
            {
                "status": status,
                "output": str(OUTPUT_PATH.relative_to(REPOSITORY_ROOT)),
                "file_count": len(expected.splitlines()),
            }
        )
    )


if __name__ == "__main__":
    main()
