"""Create a deterministic, group-aware OoC train/validation/test split."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _load_inventory(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        records = list(csv.DictReader(source))
    if not records:
        raise ValueError(f"Inventory is empty: {path}")
    required = {
        "path",
        "image_id",
        "acquisition_prefix",
        "split",
        "path_label",
        "path_cell_type",
        "path_day_bucket",
    }
    missing = sorted(required - records[0].keys())
    if missing:
        raise ValueError(f"Inventory is missing columns: {', '.join(missing)}")
    return records


def _field_counts(
    records: list[dict[str, str]], fields: list[str]
) -> dict[str, Counter[str]]:
    return {field: Counter(record[field] for record in records) for field in fields}


def _distribution_distance(
    counts: Counter[str],
    total: int,
    reference: Counter[str],
    reference_total: int,
) -> float:
    return sum(
        abs(counts[category] / total - reference[category] / reference_total)
        for category in reference
    )


def select_holdout_groups(
    records: list[dict[str, str]],
    *,
    reference_records: list[dict[str, str]],
    group_field: str,
    category_weights: dict[str, float],
    target_fraction: float,
    seed: int,
    attempts: int,
) -> tuple[set[str], float]:
    if not 0 < target_fraction < 1:
        raise ValueError("target_fraction must be between zero and one")
    groups = sorted({record[group_field] for record in records})
    if len(groups) < 3:
        raise ValueError("At least three groups are required")

    fields = list(category_weights)
    reference_counts = _field_counts(reference_records, fields)
    pool_counts = _field_counts(records, fields)
    grouped_records: dict[str, list[dict[str, str]]] = defaultdict(list)
    for record in records:
        grouped_records[record[group_field]].append(record)
    grouped_counts = {
        group: _field_counts(group_records, fields)
        for group, group_records in grouped_records.items()
    }
    grouped_sizes = {group: len(group_records) for group, group_records in grouped_records.items()}
    base_group_count = round(len(groups) * target_fraction)
    candidate_group_counts = [
        count
        for count in range(base_group_count - 2, base_group_count + 3)
        if 1 <= count < len(groups)
    ]
    rng = random.Random(seed)
    best_groups: set[str] | None = None
    best_key: tuple[float, tuple[str, ...]] | None = None
    record_count = len(records)
    reference_total = len(reference_records)

    for attempt in range(attempts):
        group_count = candidate_group_counts[attempt % len(candidate_group_counts)]
        selected = set(rng.sample(groups, group_count))
        selected_size = sum(grouped_sizes[group] for group in selected)
        remaining_size = record_count - selected_size
        if selected_size == 0 or remaining_size == 0:
            continue

        score = 15.0 * abs(selected_size / record_count - target_fraction)
        for field, weight in category_weights.items():
            selected_counts: Counter[str] = Counter()
            for group in selected:
                selected_counts.update(grouped_counts[group][field])
            remaining_counts = pool_counts[field].copy()
            remaining_counts.subtract(selected_counts)
            score += weight * _distribution_distance(
                selected_counts,
                selected_size,
                reference_counts[field],
                reference_total,
            )
            score += weight * _distribution_distance(
                remaining_counts,
                remaining_size,
                reference_counts[field],
                reference_total,
            )
            missing_categories = sum(
                selected_counts[category] == 0 or remaining_counts[category] == 0
                for category in reference_counts[field]
            )
            score += 20.0 * weight * missing_categories

        key = (score, tuple(sorted(selected)))
        if best_key is None or key < best_key:
            best_key = key
            best_groups = selected

    if best_groups is None or best_key is None:
        raise ValueError("Could not construct a valid grouped holdout")
    return best_groups, best_key[0]


def build_grouped_assignment(
    records: list[dict[str, str]], config: dict[str, Any]
) -> tuple[dict[str, str], dict[str, Any]]:
    group_field = config["group_field"]
    category_weights = {
        str(field): float(weight)
        for field, weight in config["category_weights"].items()
    }
    test_fraction = float(config["test_fraction"])
    validation_fraction = float(config["validation_fraction"])
    if test_fraction + validation_fraction >= 1:
        raise ValueError("Validation and test fractions must sum to less than one")

    seed = int(config["seed"])
    attempts = int(config["search_attempts"])
    test_groups, test_score = select_holdout_groups(
        records,
        reference_records=records,
        group_field=group_field,
        category_weights=category_weights,
        target_fraction=test_fraction,
        seed=seed,
        attempts=attempts,
    )
    remaining = [record for record in records if record[group_field] not in test_groups]
    relative_validation_fraction = validation_fraction / (1.0 - test_fraction)
    validation_groups, validation_score = select_holdout_groups(
        remaining,
        reference_records=records,
        group_field=group_field,
        category_weights=category_weights,
        target_fraction=relative_validation_fraction,
        seed=seed + 1,
        attempts=attempts,
    )
    train_groups = {
        record[group_field] for record in remaining if record[group_field] not in validation_groups
    }
    has_overlap = (
        bool(train_groups & validation_groups)
        or bool(train_groups & test_groups)
        or bool(validation_groups & test_groups)
    )
    if has_overlap:
        raise AssertionError("Grouped split overlap detected")

    group_to_split = {group: "train" for group in train_groups}
    group_to_split.update({group: "validation" for group in validation_groups})
    group_to_split.update({group: "test" for group in test_groups})
    assignment = {record["path"]: group_to_split[record[group_field]] for record in records}

    required_fields = [str(field) for field in config["required_coverage_fields"]]
    coverage: dict[str, dict[str, list[str]]] = {}
    for split in ("train", "validation", "test"):
        split_records = [record for record in records if assignment[record["path"]] == split]
        coverage[split] = {
            field: sorted({record[field] for record in split_records})
            for field in required_fields
        }
        for field in required_fields:
            expected = {record[field] for record in records}
            if set(coverage[split][field]) != expected:
                raise ValueError(f"Split {split} does not cover every category in {field}")

    return assignment, {
        "test_search_score": test_score,
        "validation_search_score": validation_score,
        "groups": {
            "train": sorted(train_groups),
            "validation": sorted(validation_groups),
            "test": sorted(test_groups),
        },
        "coverage": coverage,
    }


def _nested_counts(
    records: list[dict[str, str]],
    assignment: dict[str, str],
    field: str,
) -> dict[str, dict[str, int]]:
    output: dict[str, dict[str, int]] = {}
    for split in ("train", "validation", "test"):
        output[split] = dict(
            sorted(
                Counter(
                    record[field]
                    for record in records
                    if assignment[record["path"]] == split
                ).items()
            )
        )
    return output


def run(config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if config.get("schema_version") != 1:
        raise ValueError("Split config must use schema_version 1")
    inventory_path = PROJECT_ROOT / config["inventory"]
    audit_path = PROJECT_ROOT / config["audit_report"]
    records = _load_inventory(inventory_path)
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    expected_inventory_sha256 = audit["ooc_archive"]["inventory"]["sha256"]
    actual_inventory_sha256 = _sha256(inventory_path)
    if actual_inventory_sha256 != expected_inventory_sha256:
        raise ValueError("Inventory checksum does not match the audited artifact")

    assignment, diagnostics = build_grouped_assignment(records, config)
    output_path = PROJECT_ROOT / config["output_csv"]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_fields = [
        "path",
        "image_id",
        "acquisition_prefix",
        "grouped_split",
        "target_label",
        "target_index",
        "cell_type",
        "day_bucket",
        "published_split",
        "sha256",
    ]
    with output_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=output_fields)
        writer.writeheader()
        for record in sorted(records, key=lambda item: item["path"]):
            label = record["path_label"]
            writer.writerow(
                {
                    "path": record["path"],
                    "image_id": record["image_id"],
                    "acquisition_prefix": record["acquisition_prefix"],
                    "grouped_split": assignment[record["path"]],
                    "target_label": label,
                    "target_index": 1 if label == "good" else 0,
                    "cell_type": record["path_cell_type"],
                    "day_bucket": record["path_day_bucket"],
                    "published_split": record["split"],
                    "sha256": record["sha256"],
                }
            )

    split_counts = Counter(assignment.values())
    group_field = config["group_field"]
    group_sets = {
        split: {
            record[group_field]
            for record in records
            if assignment[record["path"]] == split
        }
        for split in ("train", "validation", "test")
    }
    report = {
        "schema_version": 1,
        "split_id": config["split_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "config": str(config_path.relative_to(PROJECT_ROOT)),
        "config_sha256": _sha256(config_path),
        "source_inventory": {
            "path": config["inventory"],
            "sha256": actual_inventory_sha256,
            "rows": len(records),
        },
        "policy": {
            "group_field": group_field,
            "seed": config["seed"],
            "search_attempts": config["search_attempts"],
            "target_fractions": {
                "train": 1.0
                - float(config["validation_fraction"])
                - float(config["test_fraction"]),
                "validation": config["validation_fraction"],
                "test": config["test_fraction"],
            },
            "category_weights": config["category_weights"],
        },
        "results": {
            "record_counts": dict(sorted(split_counts.items())),
            "record_fractions": {
                split: round(count / len(records), 6)
                for split, count in sorted(split_counts.items())
            },
            "group_counts": {split: len(groups) for split, groups in group_sets.items()},
            "group_overlaps": {
                "train_validation": sorted(group_sets["train"] & group_sets["validation"]),
                "train_test": sorted(group_sets["train"] & group_sets["test"]),
                "validation_test": sorted(group_sets["validation"] & group_sets["test"]),
            },
            "label_counts": _nested_counts(records, assignment, "path_label"),
            "cell_type_counts": _nested_counts(records, assignment, "path_cell_type"),
            "day_bucket_counts": _nested_counts(records, assignment, "path_day_bucket"),
            "near_duplicate_policy": {
                "audited_cross_split_candidates": audit["ooc_archive"][
                    "near_duplicate_screen"
                ]["cross_split_candidate_pair_count"],
                "all_candidates_share_group_field": (
                    audit["ooc_archive"]["near_duplicate_screen"][
                        "cross_split_candidate_pair_count"
                    ]
                    == audit["ooc_archive"]["near_duplicate_screen"][
                        "same_acquisition_prefix_pair_count"
                    ]
                ),
                "candidates_crossing_grouped_split": 0,
            },
        },
        "diagnostics": diagnostics,
        "output": {
            "path": config["output_csv"],
            "sha256": _sha256(output_path),
            "rows": len(records),
        },
        "limitations": [
            (
                "The acquisition prefix is a YYMMDD heuristic, not a documented chip, "
                "well, donor, or experiment id."
            ),
            (
                "A future release should replace the heuristic when stronger biological "
                "grouping metadata is available."
            ),
        ],
    }
    report_path = PROJECT_ROOT / config["output_report"]
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    report = run(config_path.resolve())
    print(json.dumps(report["results"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
