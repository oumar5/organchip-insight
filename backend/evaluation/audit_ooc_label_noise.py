"""Audit contradictory labels among visually close OoC image pairs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INVENTORY = PROJECT_ROOT / "reports/ooc-image-inventory-2026-09-16.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "reports/ooc-label-noise-v1.json"
REQUIRED_FIELDS = {
    "path",
    "acquisition_prefix",
    "split",
    "path_label",
    "path_cell_type",
    "dhash256",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_inventory(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        fields = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_FIELDS - fields)
        if missing:
            raise ValueError(f"Inventory is missing required fields: {missing}")
        rows = list(reader)
    if not rows:
        raise ValueError("Inventory is empty")
    for row in rows:
        value = row["dhash256"]
        if len(value) != 64:
            raise ValueError(f"Invalid 256-bit dHash for {row['path']}")
        try:
            int(value, 16)
        except ValueError as error:
            raise ValueError(f"Invalid 256-bit dHash for {row['path']}") from error
    return rows


def audit_rows(rows: list[dict[str, str]], maximum_distance: int) -> dict[str, Any]:
    if maximum_distance < 0 or maximum_distance > 256:
        raise ValueError("maximum_distance must be between 0 and 256")

    candidates: list[tuple[dict[str, str], dict[str, str], int]] = []
    hashes = [(row, int(row["dhash256"], 16)) for row in rows]
    for (left, left_hash), (right, right_hash) in combinations(hashes, 2):
        distance = (left_hash ^ right_hash).bit_count()
        if distance <= maximum_distance:
            candidates.append((left, right, distance))

    conflicts = [
        pair for pair in candidates if pair[0]["path_label"] != pair[1]["path_label"]
    ]
    different_cell_type = [
        pair
        for pair in candidates
        if pair[0]["path_cell_type"] != pair[1]["path_cell_type"]
    ]
    cross_split = [
        pair for pair in candidates if pair[0]["split"] != pair[1]["split"]
    ]

    return {
        "image_count": len(rows),
        "pair_count": len(rows) * (len(rows) - 1) // 2,
        "candidate_pair_count": len(candidates),
        "label_conflict_pair_count": len(conflicts),
        "different_cell_type_pair_count": len(different_cell_type),
        "cross_published_split_pair_count": len(cross_split),
        "same_acquisition_prefix_pair_count": sum(
            left["acquisition_prefix"] == right["acquisition_prefix"]
            for left, right, _distance in candidates
        ),
        "label_conflict_different_cell_type_pair_count": sum(
            left["path_cell_type"] != right["path_cell_type"]
            for left, right, _distance in conflicts
        ),
        "distance_counts": {
            str(distance): count
            for distance, count in sorted(
                Counter(distance for _left, _right, distance in candidates).items()
            )
        },
        "label_conflict_distance_counts": {
            str(distance): count
            for distance, count in sorted(
                Counter(distance for _left, _right, distance in conflicts).items()
            )
        },
    }


def build_report(inventory: Path, maximum_distance: int) -> dict[str, Any]:
    rows = load_inventory(inventory)
    return {
        "schema_version": 1,
        "audit_id": "ooc-label-noise-v1",
        "source": {
            "inventory": str(inventory.relative_to(PROJECT_ROOT)),
            "inventory_sha256": sha256_file(inventory),
        },
        "method": {
            "hash": "256-bit difference hash on a 17x16 grayscale thumbnail",
            "maximum_hamming_distance": maximum_distance,
            "pair_selection": "all unordered inventory pairs",
        },
        "results": audit_rows(rows, maximum_distance),
        "interpretation": {
            "claim": (
                "Visually close pairs can carry contradictory published labels; this is "
                "a label-noise risk, not proof that either label is wrong."
            ),
            "limitations": [
                "dHash similarity does not prove biological or acquisition identity.",
                "The audit does not estimate a population label-error rate.",
                "No image is removed or relabelled after observing model outputs.",
            ],
        },
    }


def serialized(report: dict[str, Any]) -> str:
    return json.dumps(report, indent=2, ensure_ascii=False) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, default=DEFAULT_INVENTORY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--maximum-distance", type=int, default=8)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    report = build_report(args.inventory.resolve(), args.maximum_distance)
    expected = serialized(report)
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
