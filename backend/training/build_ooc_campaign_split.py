"""Build the preregistered campaign split without evaluating a model."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from training.split_ooc import (
    _audit_grouped_near_duplicates,
    _load_inventory,
    build_grouped_assignment,
)

ROOT = Path(__file__).resolve().parents[2]
FIELDS = (
    "path",
    "image_id",
    "acquisition_prefix",
    "group_id",
    "grouped_split",
    "target_label",
    "target_index",
    "cell_type",
    "day_bucket",
    "published_split",
    "sha256",
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def campaign_lookup(audit: dict[str, Any]) -> dict[str, str]:
    primary = audit.get("primary")
    if not isinstance(primary, dict) or primary.get("gap_days") != 3:
        raise ValueError("Campaign audit does not contain the preregistered primary rule")
    lookup: dict[str, str] = {}
    for campaign in primary.get("campaigns", []):
        campaign_id = campaign.get("campaign_id")
        dates = campaign.get("dates")
        if not isinstance(campaign_id, str) or not isinstance(dates, list) or not dates:
            raise ValueError("Campaign audit contains an invalid campaign")
        for date in dates:
            if not isinstance(date, str) or date in lookup:
                raise ValueError("Campaign audit dates are invalid or duplicated")
            lookup[date] = campaign_id
    if len(lookup) != primary.get("date_count"):
        raise ValueError("Campaign audit date count is inconsistent")
    return lookup


def build(config_path: Path) -> tuple[list[dict[str, str]], dict[str, Any]]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1 or config.get("group_field") != "group_id":
        raise ValueError("Campaign split config is invalid")
    inventory_path = ROOT / config["inventory"]
    audit_path = ROOT / config["campaign_audit"]
    if sha256_file(inventory_path) != config["inventory_sha256"]:
        raise ValueError("Inventory hash mismatch")
    if sha256_file(audit_path) != config["campaign_audit_sha256"]:
        raise ValueError("Campaign audit hash mismatch")
    records = _load_inventory(inventory_path)
    lookup = campaign_lookup(json.loads(audit_path.read_text(encoding="utf-8")))
    if {record["acquisition_prefix"] for record in records} != set(lookup):
        raise ValueError("Campaign audit and inventory dates differ")
    for record in records:
        record["group_id"] = lookup[record["acquisition_prefix"]]

    assignment, diagnostics = build_grouped_assignment(records, config)
    near_duplicates = _audit_grouped_near_duplicates(
        records,
        assignment,
        maximum_distance=config["near_duplicate_maximum_hamming_distance"],
    )
    if not near_duplicates["passed"]:
        raise ValueError("Campaign split leaves near-duplicates across splits")
    rows = []
    for record in sorted(records, key=lambda item: item["path"]):
        label = record["path_label"]
        rows.append(
            {
                "path": record["path"],
                "image_id": record["image_id"],
                "acquisition_prefix": record["acquisition_prefix"],
                "group_id": record["group_id"],
                "grouped_split": assignment[record["path"]],
                "target_label": label,
                "target_index": "1" if label == "good" else "0",
                "cell_type": record["path_cell_type"],
                "day_bucket": record["path_day_bucket"],
                "published_split": record["split"],
                "sha256": record["sha256"],
            }
        )
    counts = Counter(row["grouped_split"] for row in rows)
    groups = {
        split: sorted({row["group_id"] for row in rows if row["grouped_split"] == split})
        for split in ("train", "validation", "test")
    }
    report = {
        "schema_version": 1,
        "split_id": config["split_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "scope": "assignment only; no model training or performance evaluation",
        "config": str(config_path.relative_to(ROOT)),
        "config_sha256": sha256_file(config_path),
        "inventory_sha256": config["inventory_sha256"],
        "campaign_audit_sha256": config["campaign_audit_sha256"],
        "record_counts": dict(sorted(counts.items())),
        "group_counts": {split: len(values) for split, values in groups.items()},
        "groups": groups,
        "coverage": diagnostics["coverage"],
        "search_scores": {
            "test": diagnostics["test_search_score"],
            "validation": diagnostics["validation_search_score"],
        },
        "coverage_reservation": {
            "test_minimum_remaining_groups_per_category": config[
                "test_minimum_remaining_groups_per_category"
            ],
            "validation_minimum_remaining_groups_per_category": config[
                "validation_minimum_remaining_groups_per_category"
            ],
            "reason": (
                "The unreserved preregistered search selected two of the three NHBE "
                "campaigns for test, making train/validation coverage impossible."
            ),
        },
        "near_duplicate_audit": near_duplicates,
        "limitations": [
            "Temporal campaigns are heuristic connected components, not biological IDs.",
            "Target labels were used only for category balancing, never for model selection.",
            "The test labels have been available historically; this is not a globally unseen test.",
        ],
    }
    return rows, report


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else ROOT / args.config
    config = json.loads(config_path.read_text(encoding="utf-8"))
    rows, report = build(config_path)
    outputs = {
        ROOT / config["output_csv"]: rows,
        ROOT / config["train_validation_output"]: [
            row for row in rows if row["grouped_split"] in {"train", "validation"}
        ],
        ROOT / config["test_output"]: [row for row in rows if row["grouped_split"] == "test"],
    }
    for path, selected in outputs.items():
        write_csv(path, selected)
    report["outputs"] = {
        str(path.relative_to(ROOT)): {
            "rows": len(selected),
            "sha256": sha256_file(path),
        }
        for path, selected in outputs.items()
    }
    report_path = ROOT / config["output_report"]
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "record_counts": report["record_counts"],
                "group_counts": report["group_counts"],
                "outputs": report["outputs"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
