"""Audit temporal grouping without creating a split or evaluating a model."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SPLITS = {"train", "validation", "test"}


def audit_campaigns(records: list[dict[str, str]], gap_days: int) -> dict[str, Any]:
    if isinstance(gap_days, bool) or not isinstance(gap_days, int) or gap_days < 1:
        raise ValueError("gap_days must be a positive integer")
    if not records:
        raise ValueError("Manifest is empty")
    dates: dict[str, list[dict[str, str]]] = defaultdict(list)
    seen: set[str] = set()
    for record in records:
        for name in ("path", "acquisition_prefix", "cell_type", "grouped_split"):
            if not record.get(name, "").strip():
                raise ValueError(f"Missing {name}")
        if record["path"] in seen:
            raise ValueError("Duplicate image path")
        seen.add(record["path"])
        prefix = record["acquisition_prefix"]
        if len(prefix) != 6 or not prefix.isdigit():
            raise ValueError("Expected a YYMMDD acquisition prefix")
        datetime.strptime(prefix, "%y%m%d")
        if record["grouped_split"] not in SPLITS:
            raise ValueError("Unknown grouped_split")
        dates[prefix].append(record)
    splits: dict[str, str] = {}
    for prefix, items in dates.items():
        values = {item["grouped_split"] for item in items}
        if len(values) != 1:
            raise ValueError("Historical split shares an acquisition date")
        splits[prefix] = next(iter(values))

    ordered = sorted(dates, key=lambda value: datetime.strptime(value, "%y%m%d"))
    timestamps = {value: datetime.strptime(value, "%y%m%d") for value in ordered}
    types = {prefix: {item["cell_type"] for item in items} for prefix, items in dates.items()}
    parents = {prefix: prefix for prefix in dates}

    def root(prefix: str) -> str:
        while parents[prefix] != prefix:
            parents[prefix] = parents[parents[prefix]]
            prefix = parents[prefix]
        return prefix

    edges = []
    affected_dates: set[str] = set()
    affected_date_types: set[tuple[str, str]] = set()
    for index, left in enumerate(ordered):
        for right in ordered[index + 1 :]:
            distance = (timestamps[right] - timestamps[left]).days
            if distance > gap_days:
                break
            shared = sorted(types[left] & types[right])
            if not shared:
                continue
            parents[root(right)] = root(left)
            cross_split = splits[left] != splits[right]
            edges.append(
                {
                    "dates": [left, right],
                    "gap_days": distance,
                    "shared_cell_types": shared,
                    "crosses_v1_split": cross_split,
                    "v1_splits": [splits[left], splits[right]],
                }
            )
            if cross_split:
                affected_dates.update((left, right))
                affected_date_types.update(
                    (value, kind) for value in (left, right) for kind in shared
                )

    components: dict[str, list[str]] = defaultdict(list)
    for prefix in ordered:
        components[root(prefix)].append(prefix)
    campaigns = []
    for prefixes in components.values():
        items = [item for prefix in prefixes for item in dates[prefix]]
        campaigns.append(
            {
                "campaign_id": f"campaign-{prefixes[0]}",
                "dates": prefixes,
                "span_days": (timestamps[prefixes[-1]] - timestamps[prefixes[0]]).days,
                "image_count": len(items),
                "cell_types": sorted({item["cell_type"] for item in items}),
                "v1_split_counts": dict(
                    sorted(Counter(item["grouped_split"] for item in items).items())
                ),
            }
        )
    test = [record for record in records if record["grouped_split"] == "test"]
    return {
        "gap_days": gap_days,
        "image_count": len(records),
        "date_count": len(dates),
        "campaign_count": len(campaigns),
        "cross_v1_split_edge_count": sum(edge["crosses_v1_split"] for edge in edges),
        "test_images_on_cross_split_neighbor_dates": sum(
            record["acquisition_prefix"] in affected_dates for record in test
        ),
        "test_images_with_matching_neighbor_cell_type": sum(
            (record["acquisition_prefix"], record["cell_type"]) in affected_date_types
            for record in test
        ),
        "edges": edges,
        "campaigns": campaigns,
    }


def build_report(manifest: Path, protocol: Path) -> dict[str, Any]:
    rule = json.loads(protocol.read_text(encoding="utf-8"))
    expected = {
        "schema_version": 1,
        "protocol_id": "ooc-campaign-structure-v2",
        "primary_gap_days": 3,
        "structural_sensitivity_gap_days": [1, 7],
        "edge_requires_shared_cell_type": True,
        "grouping": "connected-components-of-acquisition-dates",
        "assignment_or_model_evaluation": False,
    }
    if rule != expected:
        raise ValueError("Protocol changed: preregister a separate revision before use")
    with manifest.open(encoding="utf-8", newline="") as source:
        records = list(csv.DictReader(source))
    return {
        "schema_version": 1,
        "scope": "structural-audit-only; biological independence not established",
        "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "protocol": rule,
        "primary": audit_campaigns(records, rule["primary_gap_days"]),
        "structural_sensitivity_only": [
            audit_campaigns(records, days) for days in rule["structural_sensitivity_gap_days"]
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=ROOT / "data/splits/ooc-grouped-v1.csv")
    parser.add_argument(
        "--protocol",
        type=Path,
        default=ROOT / "backend/training/configs/ooc-campaign-audit-v2.json",
    )
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(args.manifest, args.protocol)
    # Exclusive creation protects previous audit evidence and the source manifest.
    with args.output.open("x", encoding="utf-8") as target:
        target.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
    summary = {
        key: value for key, value in report["primary"].items() if key not in {"edges", "campaigns"}
    }
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
