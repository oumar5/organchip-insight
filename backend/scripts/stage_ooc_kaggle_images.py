"""Create deterministic private Kaggle image bundles from a frozen split manifest."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXED_ZIP_TIME = (2026, 9, 16, 0, 0, 0)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_bundle(*, manifest: Path, split_role: str, output: Path) -> dict:
    if split_role not in {"train-validation", "frozen-test"}:
        raise ValueError("split_role must be train-validation or frozen-test")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite staging directory: {output}")
    with manifest.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    allowed = {"train", "validation"} if split_role == "train-validation" else {"test"}
    observed = {row["grouped_split"] for row in rows}
    if not rows or observed != allowed:
        raise ValueError(f"Manifest splits {sorted(observed)} do not match {sorted(allowed)}")
    output.mkdir(parents=True)
    archive_path = output / "images.zip"
    seen_names: set[str] = set()
    total_bytes = 0
    with zipfile.ZipFile(
        archive_path,
        "x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=6,
        allowZip64=True,
    ) as archive:
        for row in sorted(rows, key=lambda item: item["path"]):
            relative = Path(row["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"Unsafe manifest path: {relative}")
            source_path = ROOT / relative
            if not source_path.is_file() or source_path.is_symlink():
                raise ValueError(f"Missing or linked image: {relative}")
            if sha256_file(source_path) != row["sha256"]:
                raise ValueError(f"Image hash mismatch: {relative}")
            archive_name = relative.as_posix()
            if archive_name in seen_names:
                raise ValueError(f"Duplicate archive path: {archive_name}")
            seen_names.add(archive_name)
            info = zipfile.ZipInfo(archive_name, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            with (
                source_path.open("rb") as source,
                archive.open(info, "w", force_zip64=True) as target,
            ):
                shutil.copyfileobj(source, target, length=1024 * 1024)
            total_bytes += source_path.stat().st_size
    shutil.copy2(manifest, output / "split-manifest.csv")
    archive_hash = sha256_file(archive_path)
    manifest_hash = sha256_file(manifest)
    dataset_id = (
        "oumarbenlol/organchip-ooc-campaign-v2-train-validation"
        if split_role == "train-validation"
        else "oumarbenlol/organchip-ooc-campaign-v2-frozen-test"
    )
    title = (
        "OrganChip OoC Campaign v2 Train Validation"
        if split_role == "train-validation"
        else "OrganChip OoC Campaign v2 Frozen Test"
    )
    description = (
        "Private OrganChip Insight bundle derived from the OOC Image Dataset "
        "(DOI 10.5281/zenodo.10203721, CC BY 4.0). Images are selected by the "
        "preregistered temporal-campaign v2 manifest. The ZIP preserves canonical "
        "repository-relative paths. This dataset is not a performance result."
    )
    metadata = {
        "title": title,
        "id": dataset_id,
        "licenses": [{"name": "CC-BY-4.0"}],
        "subtitle": "Private reproducible OoC image partition for OrganChip Insight",
        "description": description,
        "keywords": ["biology", "microscopy", "deep learning"],
    }
    bundle = {
        "schema_version": 1,
        "dataset_id": dataset_id,
        "privacy": "private",
        "split_role": split_role,
        "source_dataset": {
            "name": "OOC Image Dataset",
            "doi": "10.5281/zenodo.10203721",
            "license": "CC-BY-4.0",
        },
        "canonical_manifest": str(manifest.relative_to(ROOT)),
        "canonical_manifest_sha256": manifest_hash,
        "image_count": len(rows),
        "uncompressed_image_bytes": total_bytes,
        "archive": {
            "path": "images.zip",
            "sha256": archive_hash,
            "size_bytes": archive_path.stat().st_size,
            "member_count": len(seen_names),
        },
        "extraction_root": ".",
    }
    (output / "dataset-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "bundle-manifest.json").write_text(
        json.dumps(bundle, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "README.md").write_text(
        f"# {title}\n\n{description}\n\n"
        f"Images: {len(rows)}. Manifest SHA-256: `{manifest_hash}`. "
        f"Archive SHA-256: `{archive_hash}`.\n",
        encoding="utf-8",
    )
    return bundle


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--split-role", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    print(
        json.dumps(
            write_bundle(
                manifest=manifest,
                split_role=args.split_role,
                output=args.output,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
