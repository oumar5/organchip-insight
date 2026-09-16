"""Audit the public OoC metadata and BBBC019 Microfluidics validation subset."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
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


def audit_ooc_datasheet(path: Path) -> dict[str, Any]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    raw_rows = list(sheet.iter_rows(values_only=True))
    headers = [str(value).strip() for value in raw_rows[0]]
    all_rows = raw_rows[1:]
    rows = [row for row in all_rows if any(value not in EMPTY for value in row)]
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


def build_report(manifest_path: Path, ooc_path: Path, bbbc_root: Path) -> dict[str, Any]:
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
        "bbbc019_microfluidic": bbbc_audit,
        "decision": {
            "safe_to_benchmark_bbbc019": bbbc_ready,
            "safe_to_train_ooc_classifier": False,
            "reason": (
                "BBBC019 image/mask pairs are complete. OoC split leakage cannot be audited "
                "until image paths or an explicit experiment/chip grouping are available."
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
            args.manifest.resolve(), args.ooc_datasheet.resolve(), args.bbbc_root.resolve()
        )
    except DatasetError as error:
        raise SystemExit(str(error)) from error
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = {
        "ooc_records": report["ooc_metadata"]["records"],
        "bbbc019_pairs": report["bbbc019_microfluidic"]["complete_pair_count"],
        "decision": report["decision"],
        "output": str(args.output),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
