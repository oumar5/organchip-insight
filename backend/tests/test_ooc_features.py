import csv
import hashlib

import numpy as np
import pytest
from PIL import Image

from training.ooc_features import (
    METADATA_COLUMNS,
    _entropy,
    _safe_ratio,
    extract_feature_table,
    extract_image_features,
    load_feature_cache,
    write_feature_cache,
)


def _sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _metadata_row(path: str = "images/field.png") -> dict[str, str]:
    return {
        "path": path,
        "image_id": "field",
        "acquisition_prefix": "240101",
        "grouped_split": "train",
        "target_label": "good",
        "target_index": "1",
        "cell_type": "synthetic",
        "day_bucket": "0-1_days",
        "published_split": "train",
        "sha256": "synthetic-sha256",
    }


def _write_split(path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=sorted(METADATA_COLUMNS))
        writer.writeheader()
        writer.writerows(rows)


def test_extract_image_features_is_deterministic_and_image_only(tmp_path) -> None:
    pixels = np.full((64, 64), 10, dtype=np.uint8)
    pixels[8:24, 8:24] = 230
    pixels[38:56, 36:54] = 200
    image_path = tmp_path / "objects.png"
    Image.fromarray(pixels).save(image_path)

    first = extract_image_features(image_path, thumbnail_size=64)
    second = extract_image_features(image_path, thumbnail_size=64)

    assert first == second
    assert len(first) == 50
    assert np.isfinite(np.asarray(list(first.values()))).all()
    assert first["segmentation_object_count"] == 2.0
    assert 0.0 < first["segmentation_foreground_fraction"] < 1.0
    assert {"target_label", "cell_type", "day_bucket"}.isdisjoint(first)


def test_extract_image_features_handles_constant_images(tmp_path) -> None:
    image_path = tmp_path / "constant.png"
    Image.fromarray(np.full((32, 32), 128, dtype=np.uint8)).save(image_path)

    features = extract_image_features(image_path, thumbnail_size=32)

    assert np.isfinite(np.asarray(list(features.values()))).all()
    assert features["intensity_std"] == pytest.approx(0.0)
    assert features["gradient_mean"] == pytest.approx(0.0)
    assert features["laplacian_variance"] == pytest.approx(0.0)
    assert features["center_outside_std_ratio"] == 0.0
    assert features["segmentation_object_count"] == 0.0


def test_numeric_helpers_handle_known_and_degenerate_inputs() -> None:
    assert _entropy(np.zeros(16, dtype=np.float32)) == pytest.approx(0.0)
    assert _entropy(np.asarray([0.0, 1.0] * 8, dtype=np.float32)) == pytest.approx(1.0)
    assert _safe_ratio(3.0, 2.0) == 1.5
    assert _safe_ratio(3.0, 0.0) == 0.0
    assert _safe_ratio(3.0, 1e-13) == 0.0


@pytest.mark.parametrize("thumbnail_size", [0, 3, 5, 30])
def test_extract_image_features_rejects_unsafe_thumbnail_sizes(
    tmp_path, thumbnail_size: int
) -> None:
    image_path = tmp_path / "image.png"
    Image.fromarray(np.zeros((8, 8), dtype=np.uint8)).save(image_path)

    with pytest.raises(ValueError, match="multiple of 4"):
        extract_image_features(image_path, thumbnail_size=thumbnail_size)


def test_extract_feature_table_does_not_promote_extra_manifest_columns(tmp_path) -> None:
    image_path = tmp_path / "field.png"
    Image.fromarray(np.zeros((16, 16), dtype=np.uint8)).save(image_path)
    split_path = tmp_path / "split.csv"
    row = {
        **_metadata_row("field.png"),
        "sha256": _sha256(image_path),
        "future_metadata": "123",
    }
    with split_path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=[*sorted(METADATA_COLUMNS), "future_metadata"])
        writer.writeheader()
        writer.writerow(row)

    rows, feature_names = extract_feature_table(
        split_path,
        tmp_path,
        thumbnail_size=16,
        workers=1,
    )

    assert "future_metadata" not in feature_names
    assert rows[0]["future_metadata"] == "123"


def test_extract_feature_table_rejects_bad_hashes_and_unsafe_paths(tmp_path) -> None:
    image_path = tmp_path / "field.png"
    Image.fromarray(np.zeros((16, 16), dtype=np.uint8)).save(image_path)
    split_path = tmp_path / "split.csv"
    _write_split(split_path, [{**_metadata_row("field.png"), "sha256": "wrong"}])

    with pytest.raises(ValueError, match="checksum mismatch"):
        extract_feature_table(split_path, tmp_path, thumbnail_size=16, workers=1)

    _write_split(
        split_path,
        [{**_metadata_row("../field.png"), "sha256": _sha256(image_path)}],
    )
    with pytest.raises(ValueError, match="escapes the project root"):
        extract_feature_table(split_path, tmp_path, thumbnail_size=16, workers=1)


def test_feature_cache_checks_hash_and_split_metadata(tmp_path) -> None:
    split_path = tmp_path / "split.csv"
    split_rows = [_metadata_row()]
    _write_split(split_path, split_rows)
    cache_path = tmp_path / "cache" / "features.csv"
    metadata_path = tmp_path / "metadata" / "features.json"
    rows = [{**split_rows[0], "group_id": "campaign-240101", "feature_a": 1.25}]
    write_feature_cache(
        rows,
        ["feature_a"],
        cache_path,
        metadata_path,
        {
            "split_sha256": "split-hash",
            "thumbnail_size": 16,
        },
    )

    loaded = load_feature_cache(
        cache_path,
        metadata_path,
        expected_split_sha256="split-hash",
        expected_thumbnail_size=16,
        expected_split_path=split_path,
    )
    assert loaded is not None
    loaded_rows, feature_names = loaded
    assert loaded_rows[0]["feature_a"] == "1.25"
    assert "group_id" not in loaded_rows[0]
    assert feature_names == ["feature_a"]

    changed_split_rows = [{**split_rows[0], "target_label": "bad", "target_index": "0"}]
    _write_split(split_path, changed_split_rows)
    assert (
        load_feature_cache(
            cache_path,
            metadata_path,
            expected_split_sha256="split-hash",
            expected_thumbnail_size=16,
            expected_split_path=split_path,
        )
        is None
    )
    _write_split(split_path, split_rows)

    cache_path.write_text(cache_path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert (
        load_feature_cache(
            cache_path,
            metadata_path,
            expected_split_sha256="split-hash",
            expected_thumbnail_size=16,
            expected_split_path=split_path,
        )
        is None
    )


def test_extract_feature_table_rejects_empty_manifests_and_invalid_workers(tmp_path) -> None:
    split_path = tmp_path / "split.csv"
    _write_split(split_path, [])

    with pytest.raises(ValueError, match="no records"):
        extract_feature_table(split_path, tmp_path, thumbnail_size=16, workers=1)
    with pytest.raises(ValueError, match="workers"):
        extract_feature_table(split_path, tmp_path, thumbnail_size=16, workers=0)
