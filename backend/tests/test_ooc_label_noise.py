from pathlib import Path

import pytest

from evaluation.audit_ooc_label_noise import audit_rows, load_inventory


def _row(
    path: str,
    dhash: int,
    *,
    label: str = "bad",
    cell_type: str = "A",
    split: str = "train",
    prefix: str = "230101",
) -> dict[str, str]:
    return {
        "path": path,
        "acquisition_prefix": prefix,
        "split": split,
        "path_label": label,
        "path_cell_type": cell_type,
        "dhash256": f"{dhash:064x}",
    }


def test_audit_rows_counts_conflicts_without_relabelling() -> None:
    rows = [
        _row("a.png", 0),
        _row("b.png", 1, label="good", cell_type="B", split="validation"),
        _row("c.png", ((1 << 9) - 1) << 1, prefix="230102"),
    ]

    result = audit_rows(rows, maximum_distance=8)

    assert result["pair_count"] == 3
    assert result["candidate_pair_count"] == 1
    assert result["label_conflict_pair_count"] == 1
    assert result["different_cell_type_pair_count"] == 1
    assert result["cross_published_split_pair_count"] == 1
    assert result["same_acquisition_prefix_pair_count"] == 1
    assert result["distance_counts"] == {"1": 1}


def test_load_inventory_rejects_invalid_hash(tmp_path: Path) -> None:
    inventory = tmp_path / "inventory.csv"
    inventory.write_text(
        "path,acquisition_prefix,split,path_label,path_cell_type,dhash256\n"
        "a.png,230101,train,bad,A,not-a-hash\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid 256-bit dHash"):
        load_inventory(inventory)
