from collections import defaultdict

from training.split_ooc import build_grouped_assignment


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
