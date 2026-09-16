"""Create the allowlisted offline source bundle for the Kaggle CNN notebook."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXED_ZIP_TIME = (2026, 9, 16, 0, 0, 0)
DATASET_ID = "oumarbenlol/organchip-insight-source-campaign-v2"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        digest.update(relative + b"\0" + bytes.fromhex(sha256_file(path)))
    return digest.hexdigest()


def source_paths(root: Path) -> tuple[Path, ...]:
    fixed = (
        root / "backend/training/__init__.py",
        root / "backend/experiments/ooc-cnn/kaggle-runtime-contract.json",
        root
        / "backend/training/configs/ooc-cnn-mobilenet-v3-small-campaign-v2.json",
        root / "data/splits/ooc-campaign-v2-lock.json",
        root / "data/splits/ooc-campaign-v2-train-validation.csv",
        root / "reports/ooc-image-inventory-2026-09-16.csv",
    )
    modules = tuple(sorted((root / "backend/training/ooc_cnn").glob("*.py")))
    paths = fixed + modules
    missing = [path for path in paths if not path.is_file() or path.is_symlink()]
    if missing:
        raise ValueError(f"Missing or linked source file: {missing[0]}")
    return paths


def write_bundle(*, output: Path, root: Path = ROOT) -> dict[str, object]:
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite staging directory: {output}")
    output.mkdir(parents=True)
    project = output / "organchip-insight"
    records: list[dict[str, object]] = []
    for source in source_paths(root):
        relative = source.relative_to(root)
        destination = project / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        records.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256_file(destination),
                "size_bytes": destination.stat().st_size,
            }
        )

    tree_hash = sha256_tree(project)
    metadata = {
        "title": "OrganChip Insight Source Campaign v2",
        "id": DATASET_ID,
        "licenses": [{"name": "other"}],
        "subtitle": "Allowlisted offline CNN source and protocol bundle",
        "description": (
            "Private reproducible source bundle for the OrganChip Insight CNN "
            "campaign-v2 validation notebook. It excludes raw images, the frozen "
            "test manifest, Git history, credentials, caches, and prior results."
        ),
    }
    manifest: dict[str, object] = {
        "schema_version": 1,
        "dataset_id": DATASET_ID,
        "privacy": "private",
        "project_directory": "organchip-insight",
        "source_tree_sha256": tree_hash,
        "file_count": len(records),
        "files": records,
    }
    (output / "dataset-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "source-bundle-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    archive_path = output / "organchip-insight-source-campaign-v2.zip"
    with zipfile.ZipFile(archive_path, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(
            item for item in output.rglob("*") if item.is_file() and item != archive_path
        ):
            relative = path.relative_to(output)
            info = zipfile.ZipInfo(relative.as_posix(), FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
    manifest["archive"] = {
        "path": archive_path.name,
        "sha256": sha256_file(archive_path),
        "size_bytes": archive_path.stat().st_size,
    }
    (output / "upload-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(write_bundle(output=args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
