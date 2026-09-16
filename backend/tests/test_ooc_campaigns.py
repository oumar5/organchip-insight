import json
from pathlib import Path

import pytest

from training.audit_ooc_campaigns import audit_campaigns, build_report


def row(date, kind="A", split="train", suffix=""):
    return {
        "path": f"{date}-{kind}-{suffix}.png",
        "acquisition_prefix": date,
        "cell_type": kind,
        "grouped_split": split,
    }


def test_campaign_transitivity_and_date_wide_grouping():
    report = audit_campaigns(
        [
            row("240101"),
            row("240104", split="validation"),
            row("240104", "B", "validation"),
            row("240107", "B", "test"),
        ],
        3,
    )
    assert report["campaign_count"] == 1
    assert report["campaigns"][0]["span_days"] == 6
    assert report["cross_v1_split_edge_count"] == 2


def test_direct_cell_type_exposure_is_not_date_wide_exposure():
    records = [row("240101"), row("240104", split="test"), row("240104", "B", "test")]
    report = audit_campaigns(records, 3)
    assert report["test_images_on_cross_split_neighbor_dates"] == 2
    assert report["test_images_with_matching_neighbor_cell_type"] == 1
    assert audit_campaigns(list(reversed(records)), 3) == report


def test_requires_common_cell_type_and_calendar_day_boundary():
    report = audit_campaigns(
        [
            row("240131"),
            row("240203", split="test"),
            row("240204", "B"),
        ],
        3,
    )
    assert report["campaign_count"] == 2
    assert report["edges"][0]["gap_days"] == 3
    assert audit_campaigns([row("240131"), row("240204")], 3)["campaign_count"] == 2


def test_exposure_counts_each_image_once():
    report = audit_campaigns(
        [
            row("240101"),
            row("240103", split="test"),
            row("240105", split="validation"),
        ],
        3,
    )
    assert report["cross_v1_split_edge_count"] == 2
    assert report["test_images_with_matching_neighbor_cell_type"] == 1


@pytest.mark.parametrize(
    "records",
    [
        [],
        [row("invalid")],
        [row("240230")],
        [row("240101"), row("240101")],
        [row("240101"), row("240101", "B", "test")],
        [row("240101", split="unknown")],
    ],
)
def test_rejects_ambiguous_manifest(records):
    with pytest.raises(ValueError):
        audit_campaigns(records, 3)


@pytest.mark.parametrize("gap", [0, -1, True, 1.5])
def test_rejects_invalid_gap(gap):
    with pytest.raises(ValueError):
        audit_campaigns([row("240101")], gap)


def test_versioned_report_matches_current_inputs():
    root = Path(__file__).resolve().parents[2]
    actual = build_report(
        root / "data/splits/ooc-grouped-v1.csv",
        root / "backend/training/configs/ooc-campaign-audit-v2.json",
    )
    expected = json.loads(
        (root / "reports/ooc-campaign-structure-v2-2026-09-16.json").read_text()
    )
    assert actual == expected
    assert actual["primary"]["test_images_with_matching_neighbor_cell_type"] == 270


def test_changed_protocol_requires_new_revision(tmp_path):
    protocol = tmp_path / "protocol.json"
    protocol.write_text('{"primary_gap_days": 7}')
    with pytest.raises(ValueError, match="preregister"):
        build_report(tmp_path / "not-read.csv", protocol)
