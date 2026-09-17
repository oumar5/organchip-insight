from evaluation.build_bbbc038_subset import ImageInventoryRow, select_diverse_images


def _row(
    image_id: str,
    width: int,
    height: int,
    mean: float,
    std: float,
) -> ImageInventoryRow:
    return ImageInventoryRow(
        image_id=image_id,
        image_path=f"images/{image_id}.png",
        mode="RGBA",
        width=width,
        height=height,
        grayscale_mean=mean,
        grayscale_std=std,
    )


def test_selection_uses_each_resolution_and_distinct_extremes() -> None:
    rows = [
        _row("a-low", 10, 10, 0.01, 0.10),
        _row("b-mid", 10, 10, 0.50, 0.20),
        _row("c-high", 10, 10, 0.99, 0.30),
        _row("d-mid", 20, 20, 0.45, 0.25),
        _row("e-std", 20, 20, 0.55, 0.99),
        _row("f-spare", 20, 20, 0.60, 0.40),
    ]

    selected = select_diverse_images(rows)
    selected_ids = [row.image_id for row, _reason in selected]
    reasons = [reason for _row, reason in selected]

    assert len(selected) == 5
    assert len(selected_ids) == len(set(selected_ids))
    assert reasons[:2] == [
        "resolution-representative-10x10",
        "resolution-representative-20x20",
    ]
    assert set(reasons[2:]) == {
        "lowest-grayscale-mean",
        "highest-grayscale-mean",
        "highest-grayscale-std",
    }
