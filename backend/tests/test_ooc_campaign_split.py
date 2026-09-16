import json
from pathlib import Path

import pytest

from training.build_ooc_campaign_split import build, campaign_lookup

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "backend/training/configs/ooc-campaign-split-v2.json"


def test_campaign_lookup_rejects_duplicate_dates():
    audit = {
        "primary": {
            "gap_days": 3,
            "date_count": 2,
            "campaigns": [
                {"campaign_id": "a", "dates": ["240101"]},
                {"campaign_id": "b", "dates": ["240101"]},
            ],
        }
    }
    with pytest.raises(ValueError, match="duplicated"):
        campaign_lookup(audit)


def test_repository_campaign_assignment_is_deterministic_and_disjoint():
    first_rows, first_report = build(CONFIG)
    second_rows, second_report = build(CONFIG)
    assert first_rows == second_rows
    assert first_report["record_counts"] == second_report["record_counts"]
    assert first_report["groups"] == second_report["groups"]
    assert len(first_rows) == 3072
    group_splits = {}
    for row in first_rows:
        group_splits.setdefault(row["group_id"], set()).add(row["grouped_split"])
    assert len(group_splits) == 29
    assert all(len(splits) == 1 for splits in group_splits.values())
    assert not first_report["near_duplicate_audit"]["cross_split_candidate_pair_count"]
    assert first_report["scope"].startswith("assignment only")


def test_campaign_split_config_keeps_preregistered_parameters():
    config = json.loads(CONFIG.read_text())
    assert config["seed"] == 20260916
    assert config["search_attempts"] == 20000
    assert config["test_minimum_remaining_groups_per_category"] == 2
    assert config["validation_minimum_remaining_groups_per_category"] == 1
    assert config["validation_fraction"] == config["test_fraction"] == 0.15
    assert config["category_weights"] == {
        "path_label": 4.0,
        "path_cell_type": 2.0,
        "path_day_bucket": 1.0,
    }
