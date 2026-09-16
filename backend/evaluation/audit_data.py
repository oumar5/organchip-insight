"""Audit the public OoC metadata and BBBC019 Microfluidics validation subset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from openpyxl import load_workbook
from PIL import Image

from app.datasets import DatasetError, load_manifest, verify_resource

PROJECT_ROOT = Path(__file__).resolve().parents[2]
EMPTY = (None, "")


def _display(value: Any) -> str:
    return "<missing>" if value in EMPTY else str(value).strip()


def _counts(values: list[Any]) -> dict[str, int]:
    return dict(sorted(Counter(_display(value) for value in values).items()))


def _number(value: Any) -> float | None:
    if value in EMPTY:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    pattern = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
    match = re.search(pattern, str(value).replace(",", ""))
    return float(match.group(0)) if match else None


def _load_ooc_rows(path: Path) -> tuple[Any, Any, list[str], list[Any], list[Any]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    raw_rows = list(sheet.iter_rows(values_only=True))
    headers = [str(value).strip() for value in raw_rows[0]]
    all_rows = raw_rows[1:]
    rows = [row for row in all_rows if any(value not in EMPTY for value in row)]
    return workbook, sheet, headers, all_rows, rows


def audit_ooc_datasheet(path: Path) -> dict[str, Any]:
    workbook, sheet, headers, all_rows, rows = _load_ooc_rows(path)
    columns = {header: [row[index] for row in rows] for index, header in enumerate(headers)}

    image_ids = [_display(value) for value in columns["imageID"]]
    duplicate_ids = sorted(
        identifier for identifier, count in Counter(image_ids).items() if count > 1
    )
    prefix_counts = Counter(
        identifier.rsplit("_", 1)[0] for identifier in image_ids if "_" in identifier
    )
    density = [_number(value) for value in columns["seeding density, cells/ml"]]
    flow = [_number(value) for value in columns["flow rate"]]

    missing = {
        header: sum(
            value in EMPTY or (isinstance(value, str) and not value.strip())
            for value in values
        )
        for header, values in columns.items()
    }
    return {
        "path": str(path.relative_to(PROJECT_ROOT)),
        "workbook_sheets": workbook.sheetnames,
        "active_sheet": sheet.title,
        "excel_rows_after_header": len(all_rows),
        "blank_rows": len(all_rows) - len(rows),
        "records": len(rows),
        "columns": headers,
        "missing_by_column": missing,
        "duplicate_image_ids": duplicate_ids,
        "label_counts_raw": _counts(columns["Decision 1/2 (good/bad)"]),
        "cell_type_counts": _counts(columns["cell type"]),
        "day_counts": _counts(columns["day"]),
        "time_after_seeding_hours_counts": _counts(columns["time after seeding, h"]),
        "seeding_density": {
            "raw_distinct_non_missing": len(
                {
                    _display(value)
                    for value in columns["seeding density, cells/ml"]
                    if value not in EMPTY
                }
            ),
            "numeric_distinct_non_missing": sorted(
                {value for value in density if value is not None}
            ),
            "unparseable_non_missing": sum(
                original not in EMPTY and parsed is None
                for original, parsed in zip(
                    columns["seeding density, cells/ml"], density, strict=True
                )
            ),
        },
        "flow_rate_ul_per_minute": {
            "raw_counts": _counts(columns["flow rate"]),
            "numeric_distinct_non_missing": sorted(
                {value for value in flow if value is not None}
            ),
            "unparseable_non_missing": sum(
                original not in EMPTY and parsed is None
                for original, parsed in zip(columns["flow rate"], flow, strict=True)
            ),
        },
        "candidate_image_id_prefixes": {
            "count": len(prefix_counts),
            "largest_groups": dict(prefix_counts.most_common(10)),
            "warning": (
                "Prefixes look like acquisition dates, but the dataset does not document them "
                "as independent experiment, chip, well, or donor identifiers."
            ),
        },
        "split_audit": {
            "status": "blocked_without_image_archive",
            "reason": (
                "The datasheet has no train/validation/test or biological group column. "
                "Published split membership only exists in the 6.7 GB image archive."
            ),
        },
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _day_bucket(value: Any) -> str | None:
    numeric = _number(value)
    if numeric is None:
        return None
    if numeric <= 1:
        return "0-1_days"
    if numeric <= 3:
        return "2-3_days"
    if numeric == 4:
        return "4_days"
    return "4+_days"


def _difference_hash(image: Image.Image) -> tuple[str, int]:
    grayscale = image.convert("L").resize((17, 16), Image.Resampling.BILINEAR)
    values = np.asarray(grayscale, dtype=np.int16)
    bits = values[:, 1:] > values[:, :-1]
    integer = int.from_bytes(np.packbits(bits).tobytes(), byteorder="big")
    return f"{integer:064x}", integer


def _grouped_hash_summary(
    inventory: list[dict[str, Any]],
    key: str,
    *,
    example_limit: int = 20,
) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in inventory:
        groups[str(item[key])].append(item)
    duplicate_groups = [items for items in groups.values() if len(items) > 1]
    cross_split_groups = [
        items for items in duplicate_groups if len({item["split"] for item in items}) > 1
    ]
    return {
        "duplicate_group_count": len(duplicate_groups),
        "cross_split_group_count": len(cross_split_groups),
        "cross_split_examples": [
            {
                key: items[0][key],
                "count": len(items),
                "splits": sorted({item["split"] for item in items}),
                "paths": [item["path"] for item in items[:5]],
            }
            for items in cross_split_groups[:example_limit]
        ],
    }


def _near_duplicate_screen(
    inventory: list[dict[str, Any]],
    *,
    maximum_distance: int = 8,
    example_limit: int = 30,
) -> dict[str, Any]:
    candidates = [(item, int(item["dhash256"], 16)) for item in inventory]
    count = 0
    same_acquisition_prefix_count = 0
    label_conflict_count = 0
    examples: list[dict[str, Any]] = []
    for index, (left, left_hash) in enumerate(candidates):
        for right, right_hash in candidates[index + 1 :]:
            if left["split"] == right["split"]:
                continue
            distance = (left_hash ^ right_hash).bit_count()
            if distance <= maximum_distance:
                count += 1
                same_prefix = left["acquisition_prefix"] == right["acquisition_prefix"]
                label_conflict = left["path_label"] != right["path_label"]
                same_acquisition_prefix_count += int(same_prefix)
                label_conflict_count += int(label_conflict)
                examples.append(
                    {
                        "distance": distance,
                        "same_acquisition_prefix": same_prefix,
                        "label_conflict": label_conflict,
                        "left": left["path"],
                        "right": right["path"],
                    }
                )
                examples.sort(
                    key=lambda item: (
                        not item["same_acquisition_prefix"],
                        not item["label_conflict"],
                        item["distance"],
                    )
                )
                del examples[example_limit:]
    return {
        "method": "256-bit difference hash on a 17x16 grayscale thumbnail",
        "maximum_hamming_distance": maximum_distance,
        "cross_split_candidate_pair_count": count,
        "same_acquisition_prefix_pair_count": same_acquisition_prefix_count,
        "label_conflict_pair_count": label_conflict_count,
        "examples": examples,
        "warning": (
            "This is a conservative visual-similarity screen, not proof that two "
            "microscopy fields are the same acquisition. Review candidates manually."
        ),
    }


def audit_ooc_archive(
    root: Path,
    datasheet_path: Path,
    inventory_path: Path,
) -> dict[str, Any]:
    _workbook, _sheet, headers, _all_rows, rows = _load_ooc_rows(datasheet_path)
    records = [dict(zip(headers, row, strict=True)) for row in rows]
    metadata_by_id = {_display(record["imageID"]): record for record in records}
    image_paths = sorted(root.rglob("*.png"))
    inventory: list[dict[str, Any]] = []
    invalid_structure: list[str] = []

    for image_path in image_paths:
        relative = image_path.relative_to(root)
        parts = relative.parts
        if len(parts) != 5:
            invalid_structure.append(str(relative))
            continue
        split, path_label, cell_folder, path_day_bucket, filename = parts
        image_id = Path(filename).stem
        metadata = metadata_by_id.get(image_id)
        metadata_cell_type = _display(metadata["cell type"]) if metadata else None
        metadata_day_bucket = _day_bucket(metadata["day"]) if metadata else None
        metadata_label = _display(metadata["Decision 1/2 (good/bad)"]) if metadata else None
        path_cell_type = cell_folder.removeprefix("cell_type_")

        with Image.open(image_path) as image:
            width, height = image.size
            mode = image.mode
            dhash, _dhash_integer = _difference_hash(image)

        inventory.append(
            {
                "path": str(image_path.relative_to(PROJECT_ROOT)),
                "image_id": image_id,
                "acquisition_prefix": image_id.rsplit("_", 1)[0],
                "split": split,
                "path_label": path_label,
                "path_cell_type": path_cell_type,
                "path_day_bucket": path_day_bucket,
                "metadata_label_raw": metadata_label,
                "metadata_cell_type": metadata_cell_type,
                "metadata_day_bucket": metadata_day_bucket,
                "metadata_present": metadata is not None,
                "cell_type_matches": metadata_cell_type == path_cell_type,
                "day_bucket_matches": metadata_day_bucket == path_day_bucket,
                "size_bytes": image_path.stat().st_size,
                "width": width,
                "height": height,
                "mode": mode,
                "sha256": _sha256(image_path),
                "dhash256": dhash,
            }
        )

    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(inventory[0]) if inventory else []
    with inventory_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(inventory)

    image_ids = {item["image_id"] for item in inventory}
    metadata_ids = set(metadata_by_id)
    label_cross_tab: dict[str, Counter[str]] = defaultdict(Counter)
    prefix_splits: dict[str, set[str]] = defaultdict(set)
    for item in inventory:
        label_cross_tab[str(item["metadata_label_raw"])][item["path_label"]] += 1
        prefix_splits[item["acquisition_prefix"]].add(item["split"])

    label_mapping = {
        label: dict(sorted(counts.items())) for label, counts in sorted(label_cross_tab.items())
    }
    one_to_one_label_mapping = (
        len(label_mapping) == 2
        and {path_label for counts in label_cross_tab.values() for path_label in counts}
        == {"good", "bad"}
        and all(len(counts) == 1 for counts in label_cross_tab.values())
    )
    shared_prefixes = {
        prefix: sorted(splits)
        for prefix, splits in sorted(prefix_splits.items())
        if len(splits) > 1
    }
    exact_hashes = _grouped_hash_summary(inventory, "sha256")
    difference_hashes = _grouped_hash_summary(inventory, "dhash256")
    near_duplicates = _near_duplicate_screen(inventory)
    cell_mismatches = [item for item in inventory if not item["cell_type_matches"]]
    day_mismatches = [item for item in inventory if not item["day_bucket_matches"]]
    split_label_counts = Counter(
        f"{item['split']}/{item['path_label']}" for item in inventory
    )
    split_cell_counts = Counter(
        f"{item['split']}/{item['path_cell_type']}" for item in inventory
    )
    archive_consistent = (
        len(inventory) == len(records) == 3072
        and not invalid_structure
        and image_ids == metadata_ids
        and one_to_one_label_mapping
        and not cell_mismatches
        and not day_mismatches
        and exact_hashes["cross_split_group_count"] == 0
    )

    return {
        "root": str(root.relative_to(PROJECT_ROOT)),
        "image_count": len(image_paths),
        "audited_image_count": len(inventory),
        "total_image_bytes": sum(int(item["size_bytes"]) for item in inventory),
        "invalid_path_structure": invalid_structure,
        "metadata_record_count": len(records),
        "missing_image_ids": sorted(metadata_ids - image_ids),
        "unknown_image_ids": sorted(image_ids - metadata_ids),
        "split_counts": _counts([item["split"] for item in inventory]),
        "path_label_counts": _counts([item["path_label"] for item in inventory]),
        "split_label_counts": dict(sorted(split_label_counts.items())),
        "split_cell_type_counts": dict(sorted(split_cell_counts.items())),
        "label_mapping_from_paths": label_mapping,
        "one_to_one_label_mapping": one_to_one_label_mapping,
        "cell_type_mismatch_count": len(cell_mismatches),
        "day_bucket_mismatch_count": len(day_mismatches),
        "mismatch_examples": [
            item["path"] for item in (cell_mismatches + day_mismatches)[:20]
        ],
        "image_dimensions": _counts(
            [f"{item['width']}x{item['height']}" for item in inventory]
        ),
        "image_modes": _counts([item["mode"] for item in inventory]),
        "exact_file_hashes": exact_hashes,
        "difference_hashes": difference_hashes,
        "near_duplicate_screen": near_duplicates,
        "acquisition_prefixes": {
            "count": len(prefix_splits),
            "shared_across_splits_count": len(shared_prefixes),
            "shared_across_splits": shared_prefixes,
            "warning": (
                "The YYMMDD-style prefix is treated as a conservative acquisition group. "
                "The dataset does not document a chip, well, donor, or experiment identifier."
            ),
        },
        "inventory": {
            "path": str(inventory_path.relative_to(PROJECT_ROOT)),
            "sha256": _sha256(inventory_path),
            "rows": len(inventory),
        },
        "archive_consistent": archive_consistent,
    }


def audit_bbbc019(root: Path) -> dict[str, Any]:
    image_dir = root / "images"
    mask_dir = root / "manual"
    image_paths = sorted(image_dir.glob("*.tif"))
    mask_paths = sorted(mask_dir.glob("*.png"))
    image_by_stem = {path.stem: path for path in image_paths}
    mask_by_stem = {path.stem.removesuffix("_manual"): path for path in mask_paths}
    missing_masks = sorted(set(image_by_stem) - set(mask_by_stem))
    masks_without_images = sorted(set(mask_by_stem) - set(image_by_stem))
    details: list[dict[str, Any]] = []

    for stem in sorted(set(image_by_stem) & set(mask_by_stem)):
        image_path = image_by_stem[stem]
        mask_path = mask_by_stem[stem]
        with Image.open(image_path) as image:
            image_mode = image.mode
            image_size = image.size
        with Image.open(mask_path) as mask:
            mask_mode = mask.mode
            mask_size = mask.size
            mask_values = np.asarray(mask)
        details.append(
            {
                "stem": stem,
                "image_size": list(image_size),
                "image_mode": image_mode,
                "mask_size": list(mask_size),
                "mask_mode": mask_mode,
                "mask_values": [int(value) for value in np.unique(mask_values)],
                "shape_matches": image_size == mask_size,
                "image_sha256": _sha256(image_path),
                "mask_sha256": _sha256(mask_path),
            }
        )

    duplicate_image_hashes = [
        digest
        for digest, count in Counter(item["image_sha256"] for item in details).items()
        if count > 1
    ]
    return {
        "root": str(root.relative_to(PROJECT_ROOT)),
        "image_count": len(image_paths),
        "manual_mask_count": len(mask_paths),
        "complete_pair_count": len(details),
        "missing_masks": missing_masks,
        "masks_without_images": masks_without_images,
        "all_shapes_match": all(item["shape_matches"] for item in details),
        "duplicate_image_hashes": duplicate_image_hashes,
        "alternate_reannotation_masks": len(list((root / "reannotation").glob("*.png"))),
        "pairs": details,
    }


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def build_report(
    manifest_path: Path,
    ooc_path: Path,
    ooc_image_root: Path,
    ooc_inventory_path: Path,
    bbbc_root: Path,
) -> dict[str, Any]:
    manifest = load_manifest(manifest_path)
    resources: list[dict[str, Any]] = []
    for resource in manifest["resources"]:
        path = PROJECT_ROOT / resource["path"]
        if path.exists():
            resources.append(verify_resource(resource, PROJECT_ROOT))
        else:
            resources.append(
                {
                    "id": resource["id"],
                    "path": resource["path"],
                    "status": "not_downloaded",
                    "large": bool(resource.get("large")),
                }
            )

    ooc_audit = audit_ooc_datasheet(ooc_path)
    ooc_archive_audit = audit_ooc_archive(
        ooc_image_root, ooc_path, ooc_inventory_path
    )
    shared_prefix_count = ooc_archive_audit["acquisition_prefixes"][
        "shared_across_splits_count"
    ]
    ooc_audit["split_audit"] = {
        "status": "audited",
        "published_splits_present": sorted(ooc_archive_audit["split_counts"]),
        "acquisition_prefixes_shared_across_splits": shared_prefix_count,
        "recommended_policy": (
            "Create a new group-aware split by acquisition prefix for the primary estimate. "
            "Keep the published split only as a secondary comparison with the paper."
        ),
    }
    bbbc_audit = audit_bbbc019(bbbc_root)
    bbbc_ready = (
        bbbc_audit["complete_pair_count"] == 13
        and not bbbc_audit["missing_masks"]
        and not bbbc_audit["masks_without_images"]
        and bbbc_audit["all_shapes_match"]
        and not bbbc_audit["duplicate_image_hashes"]
    )
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "manifest": str(manifest_path.relative_to(PROJECT_ROOT)),
        "resources": resources,
        "ooc_metadata": ooc_audit,
        "ooc_archive": ooc_archive_audit,
        "bbbc019_microfluidic": bbbc_audit,
        "decision": {
            "safe_to_benchmark_bbbc019": bbbc_ready,
            "safe_to_train_ooc_classifier": ooc_archive_audit["archive_consistent"],
            "safe_to_claim_unbiased_published_test": (
                ooc_archive_audit["archive_consistent"] and shared_prefix_count == 0
            ),
            "required_ooc_split_policy": "group by acquisition-prefix heuristic",
            "reason": (
                "OoC images, paths, labels, cell types and day buckets are internally "
                "consistent. Training is now possible, but any acquisition prefix shared "
                "between published splits makes that test estimate vulnerable to leakage."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=PROJECT_ROOT / "data/manifests/datasets.json"
    )
    parser.add_argument(
        "--ooc-datasheet",
        type=Path,
        default=PROJECT_ROOT / "data/raw/ooc/OOC_datasheet.xlsx",
    )
    parser.add_argument(
        "--ooc-image-root",
        type=Path,
        default=PROJECT_ROOT / "data/raw/ooc/OOC_image_dataset",
    )
    parser.add_argument(
        "--inventory-output",
        type=Path,
        default=PROJECT_ROOT / "reports/ooc-image-inventory-2026-09-16.csv",
    )
    parser.add_argument(
        "--bbbc-root",
        type=Path,
        default=PROJECT_ROOT / "data/raw/bbbc019/Microfluidic",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "reports/data-audit-2026-09-16.json",
    )
    args = parser.parse_args()
    try:
        report = build_report(
            args.manifest.resolve(),
            args.ooc_datasheet.resolve(),
            args.ooc_image_root.resolve(),
            args.inventory_output.resolve(),
            args.bbbc_root.resolve(),
        )
    except DatasetError as error:
        raise SystemExit(str(error)) from error
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = {
        "ooc_records": report["ooc_metadata"]["records"],
        "ooc_images": report["ooc_archive"]["audited_image_count"],
        "bbbc019_pairs": report["bbbc019_microfluidic"]["complete_pair_count"],
        "decision": report["decision"],
        "output": str(args.output),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
