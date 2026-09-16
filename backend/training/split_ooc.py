"""Create a deterministic, group-aware OoC train/validation/test split."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import random
import re
import subprocess
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SPLITS = ("train", "validation", "test")
LABELS = ("bad", "good")
HEX_256_PATTERN = re.compile(r"[0-9a-fA-F]{64}")


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
        "width",
        "height",
        "mode",
        "sha256",
        "dhash256",
    }
    missing = sorted(required - records[0].keys())
    if missing:
        raise ValueError(f"Inventory is missing columns: {', '.join(missing)}")

    paths = [record["path"] for record in records]
    duplicate_paths = sorted(path for path, count in Counter(paths).items() if count > 1)
    if duplicate_paths:
        raise ValueError(f"Inventory contains duplicate paths: {duplicate_paths[0]}")

    for row_number, record in enumerate(records, start=2):
        for field in required:
            value = record.get(field)
            if value is None or not value.strip():
                raise ValueError(f"Inventory row {row_number} has an empty {field}")
        if record["path_label"] not in LABELS:
            raise ValueError(
                f"Inventory row {row_number} has an unsupported label: {record['path_label']}"
            )
        for field in ("sha256", "dhash256"):
            if HEX_256_PATTERN.fullmatch(record[field]) is None:
                raise ValueError(
                    f"Inventory row {row_number} has an invalid {field}: {record[field]}"
                )
        for field in ("width", "height"):
            try:
                value = int(record[field])
            except ValueError as error:
                raise ValueError(
                    f"Inventory row {row_number} has an invalid {field}: {record[field]}"
                ) from error
            if value <= 0:
                raise ValueError(f"Inventory row {row_number} has a non-positive {field}: {value}")
    return records


def _field_counts(records: list[dict[str, str]], fields: list[str]) -> dict[str, Counter[str]]:
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
    minimum_remaining_groups_per_category: int = 0,
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
    if (
        isinstance(minimum_remaining_groups_per_category, bool)
        or not isinstance(minimum_remaining_groups_per_category, int)
        or minimum_remaining_groups_per_category < 0
    ):
        raise ValueError("minimum remaining groups per category must be non-negative")
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

        if minimum_remaining_groups_per_category:
            feasible = True
            for field in fields:
                for category in reference_counts[field]:
                    selected_has_category = any(
                        grouped_counts[group][field][category] > 0 for group in selected
                    )
                    remaining_group_count = sum(
                        grouped_counts[group][field][category] > 0
                        for group in groups
                        if group not in selected
                    )
                    if (
                        not selected_has_category
                        or remaining_group_count < minimum_remaining_groups_per_category
                    ):
                        feasible = False
                        break
                if not feasible:
                    break
            if not feasible:
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
        str(field): float(weight) for field, weight in config["category_weights"].items()
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
        minimum_remaining_groups_per_category=int(
            config.get("test_minimum_remaining_groups_per_category", 0)
        ),
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
        minimum_remaining_groups_per_category=int(
            config.get("validation_minimum_remaining_groups_per_category", 0)
        ),
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
            field: sorted({record[field] for record in split_records}) for field in required_fields
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
    for split in SPLITS:
        output[split] = dict(
            sorted(
                Counter(
                    record[field] for record in records if assignment[record["path"]] == split
                ).items()
            )
        )
    return output


def _audit_grouped_near_duplicates(
    records: list[dict[str, str]],
    assignment: dict[str, str],
    *,
    maximum_distance: int,
    example_limit: int = 30,
) -> dict[str, Any]:
    if (
        isinstance(maximum_distance, bool)
        or not isinstance(maximum_distance, int)
        or not 0 <= maximum_distance <= 256
    ):
        raise ValueError("maximum_distance must be an integer between zero and 256")
    if isinstance(example_limit, bool) or not isinstance(example_limit, int) or example_limit < 0:
        raise ValueError("example_limit must be non-negative")

    grouped: dict[str, list[tuple[dict[str, str], int]]] = {split: [] for split in SPLITS}
    for record in sorted(records, key=lambda item: item["path"]):
        split = assignment.get(record["path"])
        if split not in grouped:
            raise ValueError(f"Missing or unsupported grouped split for {record['path']}")
        grouped[split].append((record, int(record["dhash256"], 16)))

    pair_count = 0
    candidate_count = 0
    same_prefix_count = 0
    label_conflict_count = 0
    exact_file_match_count = 0
    distance_counts: Counter[int] = Counter()
    split_pairs: dict[str, dict[str, int]] = {}
    ranked_examples: list[tuple[tuple[bool, int, str, str], dict[str, Any]]] = []

    for left_index, left_split in enumerate(SPLITS):
        for right_split in SPLITS[left_index + 1 :]:
            split_pair = f"{left_split}_{right_split}"
            compared = len(grouped[left_split]) * len(grouped[right_split])
            pair_count += compared
            split_candidate_count = 0
            for left, left_hash in grouped[left_split]:
                for right, right_hash in grouped[right_split]:
                    distance = (left_hash ^ right_hash).bit_count()
                    if distance > maximum_distance:
                        continue
                    split_candidate_count += 1
                    candidate_count += 1
                    distance_counts[distance] += 1
                    same_prefix = left["acquisition_prefix"] == right["acquisition_prefix"]
                    label_conflict = left["path_label"] != right["path_label"]
                    exact_file_match = left["sha256"] == right["sha256"]
                    same_prefix_count += int(same_prefix)
                    label_conflict_count += int(label_conflict)
                    exact_file_match_count += int(exact_file_match)
                    example = {
                        "distance": distance,
                        "label_conflict": label_conflict,
                        "same_acquisition_prefix": same_prefix,
                        "exact_file_match": exact_file_match,
                        "left_split": left_split,
                        "right_split": right_split,
                        "left": left["path"],
                        "right": right["path"],
                    }
                    if example_limit:
                        rank = (
                            not label_conflict,
                            distance,
                            left["path"],
                            right["path"],
                        )
                        bisect.insort(ranked_examples, (rank, example))
                        del ranked_examples[example_limit:]
            split_pairs[split_pair] = {
                "pairs_examined": compared,
                "candidate_pairs": split_candidate_count,
            }

    return {
        "scope": "all unordered image pairs assigned to different grouped splits",
        "complete": True,
        "method": "256-bit difference hash on a 17x16 grayscale thumbnail",
        "maximum_hamming_distance": maximum_distance,
        "cross_split_pair_count": pair_count,
        "cross_split_candidate_pair_count": candidate_count,
        "same_acquisition_prefix_pair_count": same_prefix_count,
        "label_conflict_pair_count": label_conflict_count,
        "exact_file_match_pair_count": exact_file_match_count,
        "distance_counts": {
            str(distance): count for distance, count in sorted(distance_counts.items())
        },
        "split_pairs": split_pairs,
        "examples": [example for _rank, example in ranked_examples],
        "passed": candidate_count == 0,
        "warning": (
            "This exhaustively screens the configured difference-hash distance; it "
            "does not prove the absence of duplicates under rotations, crops or other "
            "transformations."
        ),
    }


def _confounder_category(record: dict[str, str], feature: str) -> str:
    resolution = f"{record['width']}x{record['height']}"
    if feature == "mode":
        return record["mode"]
    if feature == "resolution":
        return resolution
    if feature == "mode_resolution":
        return f"{record['mode']}/{resolution}"
    raise ValueError(f"Unsupported confounder feature: {feature}")


def _roc_auc(labels: list[int], probabilities: list[float]) -> float | None:
    positive_count = sum(labels)
    negative_count = len(labels) - positive_count
    if positive_count == 0 or negative_count == 0:
        return None

    ranked = sorted(zip(probabilities, labels, strict=True))
    positive_rank_sum = 0.0
    start = 0
    while start < len(ranked):
        end = start + 1
        while end < len(ranked) and ranked[end][0] == ranked[start][0]:
            end += 1
        average_rank = ((start + 1) + end) / 2.0
        positive_rank_sum += average_rank * sum(label for _probability, label in ranked[start:end])
        start = end
    return (positive_rank_sum - positive_count * (positive_count + 1) / 2.0) / (
        positive_count * negative_count
    )


def _binary_metrics(labels: list[int], probabilities: list[float]) -> dict[str, Any]:
    if not labels or len(labels) != len(probabilities):
        raise ValueError("Labels and probabilities must have the same non-zero length")
    predictions = [int(probability >= 0.5) for probability in probabilities]
    true_negative = sum(
        label == 0 and prediction == 0
        for label, prediction in zip(labels, predictions, strict=True)
    )
    false_positive = sum(
        label == 0 and prediction == 1
        for label, prediction in zip(labels, predictions, strict=True)
    )
    false_negative = sum(
        label == 1 and prediction == 0
        for label, prediction in zip(labels, predictions, strict=True)
    )
    true_positive = sum(
        label == 1 and prediction == 1
        for label, prediction in zip(labels, predictions, strict=True)
    )
    both_classes = (true_negative + false_positive) > 0 and (false_negative + true_positive) > 0
    balanced_accuracy: float | None = None
    macro_f1: float | None = None
    if both_classes:
        specificity = true_negative / (true_negative + false_positive)
        sensitivity = true_positive / (true_positive + false_negative)
        balanced_accuracy = (specificity + sensitivity) / 2.0
        bad_denominator = 2 * true_negative + false_positive + false_negative
        good_denominator = 2 * true_positive + false_positive + false_negative
        bad_f1 = 2 * true_negative / bad_denominator if bad_denominator else 0.0
        good_f1 = 2 * true_positive / good_denominator if good_denominator else 0.0
        macro_f1 = (bad_f1 + good_f1) / 2.0

    def rounded(value: float | None) -> float | None:
        return round(value, 6) if value is not None else None

    return {
        "count": len(labels),
        "class_counts": {
            "bad": true_negative + false_positive,
            "good": false_negative + true_positive,
        },
        "confusion_matrix": {
            "labels": list(LABELS),
            "values": [[true_negative, false_positive], [false_negative, true_positive]],
        },
        "accuracy": round((true_negative + true_positive) / len(labels), 6),
        "balanced_accuracy": rounded(balanced_accuracy),
        "macro_f1": rounded(macro_f1),
        "roc_auc": rounded(_roc_auc(labels, probabilities)),
    }


def _categorical_shortcut_baseline(
    records: list[dict[str, str]],
    assignment: dict[str, str],
    *,
    feature: str,
) -> dict[str, Any]:
    train_counts: dict[str, Counter[str]] = defaultdict(Counter)
    global_train_counts: Counter[str] = Counter()
    for record in records:
        if assignment[record["path"]] != "train":
            continue
        label = record["path_label"]
        category = _confounder_category(record, feature)
        train_counts[category][label] += 1
        global_train_counts[label] += 1
    if not global_train_counts:
        raise ValueError("The grouped assignment contains no training records")

    def probability_good(counts: Counter[str]) -> float:
        return (counts["good"] + 1.0) / (sum(counts.values()) + 2.0)

    global_probability = probability_good(global_train_counts)
    category_probabilities = {
        category: probability_good(counts) for category, counts in sorted(train_counts.items())
    }
    evaluations: dict[str, Any] = {}
    for split in SPLITS:
        split_records = sorted(
            (record for record in records if assignment[record["path"]] == split),
            key=lambda item: item["path"],
        )
        labels = [int(record["path_label"] == "good") for record in split_records]
        categories = [_confounder_category(record, feature) for record in split_records]
        probabilities = [
            category_probabilities.get(category, global_probability) for category in categories
        ]
        evaluations[split] = {
            **_binary_metrics(labels, probabilities),
            "unseen_categories": sorted(set(categories) - set(category_probabilities)),
        }

    return {
        "feature": feature,
        "fit_split": "train",
        "label": "good",
        "smoothing": "Laplace alpha=1",
        "threshold": 0.5,
        "threshold_selection": "fixed a priori; no validation or test selection",
        "unseen_category_policy": "smoothed global training-label rate",
        "global_train_probability_good": round(global_probability, 6),
        "train_categories": {
            category: {
                "bad": train_counts[category]["bad"],
                "good": train_counts[category]["good"],
                "probability_good": round(category_probabilities[category], 6),
            }
            for category in sorted(train_counts)
        },
        "metrics": evaluations,
    }


def _build_confounder_audit(
    records: list[dict[str, str]], assignment: dict[str, str]
) -> dict[str, Any]:
    features = ("mode", "resolution", "mode_resolution")
    distributions: dict[str, Any] = {}
    for feature in features:
        categories = sorted({_confounder_category(record, feature) for record in records})
        by_split: dict[str, Any] = {}
        for split in SPLITS:
            counts: dict[str, Counter[str]] = defaultdict(Counter)
            for record in records:
                if assignment[record["path"]] == split:
                    counts[_confounder_category(record, feature)][record["path_label"]] += 1
            by_split[split] = {
                category: {
                    "bad": counts[category]["bad"],
                    "good": counts[category]["good"],
                    "total": sum(counts[category].values()),
                    "good_rate": (
                        round(
                            counts[category]["good"] / sum(counts[category].values()),
                            6,
                        )
                        if counts[category]
                        else None
                    ),
                }
                for category in categories
            }
        distributions[feature] = {
            "categories": categories,
            "by_split": by_split,
        }

    return {
        "status": "potential acquisition shortcut detected",
        "interpretation": (
            "Mode and pixel dimensions are acquisition properties, not biological "
            "quality evidence. Predictive performance from these fields indicates a "
            "shortcut risk for image models."
        ),
        "distributions": distributions,
        "train_only_categorical_baselines": {
            feature: _categorical_shortcut_baseline(records, assignment, feature=feature)
            for feature in features
        },
    }


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
    maximum_distance = config.get("near_duplicate_maximum_hamming_distance")
    if isinstance(maximum_distance, bool) or not isinstance(maximum_distance, int):
        raise ValueError("near_duplicate_maximum_hamming_distance must be an integer")
    near_duplicate_audit = _audit_grouped_near_duplicates(
        records,
        assignment,
        maximum_distance=maximum_distance,
    )
    confounder_audit = _build_confounder_audit(records, assignment)
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
        split: {record[group_field] for record in records if assignment[record["path"]] == split}
        for split in SPLITS
    }
    report = {
        "schema_version": 1,
        "split_id": config["split_id"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "git_commit": _git_commit(),
        "implementation": {
            "path": str(Path(__file__).resolve().relative_to(PROJECT_ROOT)),
            "sha256": _sha256(Path(__file__).resolve()),
        },
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
            "near_duplicate_maximum_hamming_distance": maximum_distance,
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
            "near_duplicate_audit": near_duplicate_audit,
            "confounder_audit": confounder_audit,
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
            (
                "The exhaustive near-duplicate claim is limited to the configured "
                "difference-hash distance and does not cover every possible image "
                "transformation."
            ),
            (
                "Mode and resolution are strongly associated with the target label; CNN "
                "results must be compared with the train-only categorical shortcut "
                "baselines in this report."
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
