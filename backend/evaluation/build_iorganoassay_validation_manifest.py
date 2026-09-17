"""Build the locked manifest for the iOrganoAssay v1.1.0 validation subset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = (
    PROJECT_ROOT
    / "data/raw/iorganoassay/iOrganoAssay v1.1.0/6.Validation"
)
DEFAULT_OUTPUT = PROJECT_ROOT / "data/manifests/iorganoassay-validation-v1.1.0.json"
CONDITIONS = ("Ctrl", "DSS")
SAMPLE_COUNT_PER_CONDITION = 14


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _file_record(path: Path, root: Path) -> dict[str, Any]:
    with Image.open(path) as image:
        width, height = image.size
        mode = image.mode
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "relative_path": str(path.relative_to(root)),
        "size_bytes": path.stat().st_size,
        "sha256": sha256_file(path),
        "width": width,
        "height": height,
        "mode": mode,
    }


def build_manifest(root: Path) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        condition_dir = root / condition
        if not condition_dir.is_dir():
            raise ValueError(f"Missing validation condition directory: {condition_dir}")
        for index in range(1, SAMPLE_COUNT_PER_CONDITION + 1):
            sample_id = f"{condition}_{index:02d}"
            paths = {
                "brightfield": condition_dir / f"{sample_id}_BF.jpg",
                "ground_truth": condition_dir / f"{sample_id}_GT.jpg",
                "reference_segmentation": condition_dir / f"{sample_id}_Seg.jpg",
            }
            missing = [role for role, path in paths.items() if not path.is_file()]
            if missing:
                raise ValueError(f"Missing files for {sample_id}: {missing}")
            records = {role: _file_record(path, root) for role, path in paths.items()}
            ground_truth_shape = (
                records["ground_truth"]["width"],
                records["ground_truth"]["height"],
            )
            segmentation_shape = (
                records["reference_segmentation"]["width"],
                records["reference_segmentation"]["height"],
            )
            if ground_truth_shape != segmentation_shape:
                raise ValueError(f"GT/Seg shape mismatch for {sample_id}")
            samples.append(
                {
                    "sample_id": sample_id,
                    "condition": condition,
                    "files": records,
                }
            )

    discovered = {path.resolve() for path in root.rglob("*.jpg")}
    declared = {
        (PROJECT_ROOT / record["path"]).resolve()
        for sample in samples
        for record in sample["files"].values()
    }
    if discovered != declared:
        raise ValueError(
            f"Validation files differ from the fixed 28 triples: "
            f"extra={len(discovered - declared)}, missing={len(declared - discovered)}"
        )

    return {
        "schema_version": 1,
        "manifest_id": "iorganoassay-validation-v1.1.0",
        "dataset": {
            "name": "iOrganoAssay: Microscopy Image Dataset for Organoid Assessment Assays",
            "version": "v1.1.0",
            "zenodo_record": "20351867",
            "doi": "10.5281/zenodo.20351867",
            "license": "CC0-1.0",
            "archive_size_bytes": 1817410571,
            "archive_md5": "3cd6380e9413b977fdc531f32338ccd2",
        },
        "root": str(root.relative_to(PROJECT_ROOT)),
        "sample_count": len(samples),
        "conditions": {condition: SAMPLE_COUNT_PER_CONDITION for condition in CONDITIONS},
        "samples": samples,
    }


def serialized(manifest: dict[str, Any]) -> str:
    return json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    manifest = build_manifest(args.root.resolve())
    expected = serialized(manifest)
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"OUTDATED: {args.output}")
        print(f"OK: {args.output}")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(expected, encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
