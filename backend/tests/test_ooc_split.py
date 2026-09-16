import csv
from collections import defaultdict
from pathlib import Path

import pytest

from training.split_ooc import (
    PROJECT_ROOT,
    _audit_grouped_near_duplicates,
    _build_confounder_audit,
    _load_inventory,
    build_grouped_assignment,
)


def _audit_record(
    path: str,
    *,
    dhash: int,
    label: str = "bad",
    prefix: str = "group-a",
    published_split: str = "train",
    mode: str = "L",
    width: str = "2056",
    height: str = "1542",
) -> dict[str, str]:
    return {
        "path": path,
        "image_id": Path(path).stem,
        "acquisition_prefix": prefix,
        "split": published_split,
        "path_label": label,
        "path_cell_type": "A",
        "path_day_bucket": "early",
        "width": width,
        "height": height,
        "mode": mode,
        "sha256": f"{dhash + 100:064x}",
        "dhash256": f"{dhash:064x}",
    }


def test_grouped_split_is_deterministic_and_disjoint() -> None:
    records = []
    labels = ["bad", "good"]
    cells = ["A", "B"]
    days = ["early", "late"]
    for group_index in range(18):
        for item_index in range(8):
            records.append(
                {
                    "path": f"group-{group_index}/image-{item_index}.png",
                    "acquisition_prefix": f"group-{group_index}",
                    "path_label": labels[item_index % 2],
                    "path_cell_type": cells[(item_index // 2) % 2],
                    "path_day_bucket": days[(item_index // 4) % 2],
                }
            )
    config = {
        "group_field": "acquisition_prefix",
        "category_weights": {
            "path_label": 4.0,
            "path_cell_type": 2.0,
            "path_day_bucket": 1.0,
        },
        "test_fraction": 0.15,
        "validation_fraction": 0.15,
        "seed": 17,
        "search_attempts": 500,
        "required_coverage_fields": [
            "path_label",
            "path_cell_type",
            "path_day_bucket",
        ],
    }

    first, first_diagnostics = build_grouped_assignment(records, config)
    second, second_diagnostics = build_grouped_assignment(records, config)

    assert first == second
    assert first_diagnostics == second_diagnostics
    group_splits = defaultdict(set)
    for record in records:
        group_splits[record["acquisition_prefix"]].add(first[record["path"]])
    assert all(len(splits) == 1 for splits in group_splits.values())
    assert set(first.values()) == {"train", "validation", "test"}


def test_near_duplicate_audit_recomputes_all_grouped_cross_split_pairs() -> None:
    records = [
        _audit_record("a.png", dhash=0, prefix="group-a", label="bad"),
        _audit_record(
            "b.png",
            dhash=(1 << 8) - 1,
            prefix="group-b",
            label="good",
        ),
    ]
    assignment = {"a.png": "train", "b.png": "validation"}

    report = _audit_grouped_near_duplicates(records, assignment, maximum_distance=8)
    reversed_report = _audit_grouped_near_duplicates(
        list(reversed(records)), assignment, maximum_distance=8
    )

    assert report == reversed_report
    assert report["cross_split_pair_count"] == 1
    assert report["cross_split_candidate_pair_count"] == 1
    assert report["label_conflict_pair_count"] == 1
    assert report["same_acquisition_prefix_pair_count"] == 0
    assert report["split_pairs"]["train_validation"] == {
        "pairs_examined": 1,
        "candidate_pairs": 1,
    }
    assert report["examples"][0]["distance"] == 8
    assert not report["passed"]


def test_near_duplicate_audit_excludes_distance_nine_and_same_grouped_split() -> None:
    records = [
        _audit_record("a.png", dhash=0),
        _audit_record("b.png", dhash=(1 << 9) - 1, prefix="group-b"),
    ]

    cross_split = _audit_grouped_near_duplicates(
        records,
        {"a.png": "train", "b.png": "test"},
        maximum_distance=8,
    )
    same_split = _audit_grouped_near_duplicates(
        records,
        {"a.png": "train", "b.png": "train"},
        maximum_distance=8,
    )

    assert cross_split["cross_split_pair_count"] == 1
    assert cross_split["cross_split_candidate_pair_count"] == 0
    assert cross_split["passed"]
    assert same_split["cross_split_pair_count"] == 0
    assert same_split["cross_split_candidate_pair_count"] == 0


def test_confounder_baseline_is_fit_only_on_train() -> None:
    records = [
        _audit_record("train-bad-1.png", dhash=1, label="bad"),
        _audit_record("train-bad-2.png", dhash=2, label="bad"),
        _audit_record(
            "train-good-1.png",
            dhash=3,
            label="good",
            mode="RGB",
            width="2048",
            height="1536",
        ),
        _audit_record(
            "train-good-2.png",
            dhash=4,
            label="good",
            mode="RGB",
            width="2048",
            height="1536",
        ),
        _audit_record("validation.png", dhash=5, label="good"),
        _audit_record(
            "test.png",
            dhash=6,
            label="bad",
            mode="RGBA",
            width="512",
            height="512",
        ),
    ]
    assignment = {
        "train-bad-1.png": "train",
        "train-bad-2.png": "train",
        "train-good-1.png": "train",
        "train-good-2.png": "train",
        "validation.png": "validation",
        "test.png": "test",
    }

    first = _build_confounder_audit(records, assignment)
    changed_holdout = [dict(record) for record in records]
    for record in changed_holdout:
        if assignment[record["path"]] != "train":
            record["path_label"] = "good" if record["path_label"] == "bad" else "bad"
    second = _build_confounder_audit(changed_holdout, assignment)
    first_model = first["train_only_categorical_baselines"]["mode"]
    second_model = second["train_only_categorical_baselines"]["mode"]

    assert first_model["train_categories"] == second_model["train_categories"]
    assert first_model["global_train_probability_good"] == 0.5
    assert first_model["train_categories"]["L"]["probability_good"] == 0.25
    assert first_model["train_categories"]["RGB"]["probability_good"] == 0.75
    assert first_model["metrics"]["test"]["unseen_categories"] == ["RGBA"]


def test_inventory_validation_rejects_duplicate_paths(tmp_path: Path) -> None:
    path = tmp_path / "inventory.csv"
    records = [_audit_record("same.png", dhash=1), _audit_record("same.png", dhash=2)]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)

    with pytest.raises(ValueError, match="duplicate paths"):
        _load_inventory(path)


def test_inventory_validation_rejects_invalid_dhash(tmp_path: Path) -> None:
    path = tmp_path / "inventory.csv"
    record = _audit_record("image.png", dhash=1)
    record["dhash256"] = "not-a-hash"
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(record))
        writer.writeheader()
        writer.writerow(record)

    with pytest.raises(ValueError, match="invalid dhash256"):
        _load_inventory(path)


def test_inventory_validation_rejects_missing_required_column(tmp_path: Path) -> None:
    path = tmp_path / "inventory.csv"
    record = _audit_record("image.png", dhash=1)
    del record["mode"]
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(record))
        writer.writeheader()
        writer.writerow(record)

    with pytest.raises(ValueError, match="missing columns: mode"):
        _load_inventory(path)


def test_committed_grouped_split_exhaustively_has_no_near_duplicates() -> None:
    records = _load_inventory(PROJECT_ROOT / "reports/ooc-image-inventory-2026-09-16.csv")
    with (PROJECT_ROOT / "data/splits/ooc-grouped-v1.csv").open(
        encoding="utf-8", newline=""
    ) as source:
        assignment = {row["path"]: row["grouped_split"] for row in csv.DictReader(source)}

    report = _audit_grouped_near_duplicates(records, assignment, maximum_distance=8)

    assert report["cross_split_pair_count"] == 2_216_621
    assert report["cross_split_candidate_pair_count"] == 0
    assert report["passed"]
