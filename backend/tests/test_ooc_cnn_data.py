from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from PIL import Image

from training.ooc_cnn.dataset import (
    ManifestImageDataset,
    resolve_record_path,
    select_smoke_records,
)
from training.ooc_cnn.manifests import ManifestRecord
from training.ooc_cnn.model import build_mobilenet_v3_small
from training.ooc_cnn.preprocessing import (
    PADDING_RGB,
    force_grayscale_rgb,
    resize_and_pad,
)


def _record(
    path: str,
    *,
    split: str = "train",
    label: str = "good",
    group: str = "230101",
    digest: str = "a" * 64,
) -> ManifestRecord:
    return ManifestRecord(
        path=path,
        image_id=Path(path).stem,
        acquisition_prefix=group,
        grouped_split=split,  # type: ignore[arg-type]
        target_label=label,
        target_index=1 if label == "good" else 0,
        cell_type="A549",
        day_bucket="0-1_days",
        published_split="train",
        sha256=digest,
    )


def test_resize_and_pad_preserves_complete_landscape_image() -> None:
    source = Image.new("L", (40, 20), color=255)

    result = resize_and_pad(source, size=224)

    assert result.mode == "RGB"
    assert result.size == (224, 224)
    assert result.getpixel((112, 55)) == PADDING_RGB
    assert result.getpixel((112, 56)) == (255, 255, 255)
    assert result.getpixel((112, 167)) == (255, 255, 255)
    assert result.getpixel((112, 168)) == PADDING_RGB


def test_grayscale_ablation_removes_chroma_but_keeps_three_channels() -> None:
    source = Image.new("RGB", (2, 1))
    source.putdata([(255, 0, 0), (0, 255, 0)])

    result = force_grayscale_rgb(source)

    assert result.mode == "RGB"
    assert result.getpixel((0, 0))[0] == result.getpixel((0, 0))[1]
    assert result.getpixel((0, 0))[1] == result.getpixel((0, 0))[2]
    assert result.getpixel((0, 0)) != result.getpixel((1, 0))


def test_manifest_dataset_forces_rgb_and_validates_checksum(tmp_path: Path) -> None:
    image_path = tmp_path / "images" / "sample.png"
    image_path.parent.mkdir()
    Image.new("L", (12, 8), color=127).save(image_path)
    digest = hashlib.sha256(image_path.read_bytes()).hexdigest()
    record = _record("images/sample.png", digest=digest)
    dataset = ManifestImageDataset(
        [record],
        tmp_path,
        transform=lambda image: (image.mode, image.size),
        verify_hashes=True,
    )

    image_description, target = dataset[0]

    assert image_description == ("RGB", (12, 8))
    assert target == 1
    assert dataset.record_at(0) == record
    assert resolve_record_path(record, tmp_path) == image_path


def test_manifest_record_rejects_path_traversal() -> None:
    with pytest.raises(ValueError, match="stay inside the project root"):
        resolve_record_path(
            _record("../outside.png"),
            Path.cwd(),
            require_file=False,
        )


def test_manifest_path_rejects_symlink_that_escapes_root(tmp_path: Path) -> None:
    root = tmp_path / "project"
    root.mkdir()
    outside = tmp_path / "outside.png"
    Image.new("RGB", (2, 2)).save(outside)
    link = root / "linked.png"
    try:
        link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"symlinks are unavailable: {error}")

    with pytest.raises(ValueError, match="escapes the project root"):
        resolve_record_path(_record("linked.png"), root)


def test_smoke_sampling_is_deterministic_and_stratified() -> None:
    records = [
        _record(
            f"images/{split}-{label}-{group}-{index}.png",
            split=split,
            label=label,
            group=group,
            digest=f"{counter:064x}",
        )
        for counter, (split, label, group, index) in enumerate(
            (
                ("train", "bad", "g1", 1),
                ("train", "bad", "g1", 2),
                ("train", "good", "g1", 1),
                ("train", "good", "g1", 2),
                ("validation", "bad", "g2", 1),
                ("validation", "bad", "g2", 2),
                ("validation", "good", "g2", 1),
                ("validation", "good", "g2", 2),
                ("test", "bad", "g3", 1),
                ("test", "good", "g3", 1),
            ),
            start=1,
        )
    ]

    limits = {"train": 2, "validation": 2}
    first = select_smoke_records(records, seed=17, max_records_by_split=limits)
    second = select_smoke_records(
        reversed(records),
        seed=17,
        max_records_by_split=limits,
    )

    assert [record.path for record in first] == [record.path for record in second]
    assert len(first) == 4
    assert {record.grouped_split for record in first} == {"train", "validation"}
    assert len(
        {
            (record.grouped_split, record.target_label, record.acquisition_prefix)
            for record in first
        }
    ) == len(first)


def test_model_requires_hash_for_every_local_weights_file(tmp_path: Path) -> None:
    weights = tmp_path / "weights.pt"
    weights.write_bytes(b"not-a-checkpoint")

    with pytest.raises(ValueError, match="expected_sha256 is required"):
        build_mobilenet_v3_small(weights=weights)
    with pytest.raises(ValueError, match="weights checksum mismatch"):
        build_mobilenet_v3_small(weights=weights, expected_sha256="0" * 64)
    with pytest.raises(ValueError, match="must be omitted"):
        build_mobilenet_v3_small(weights="none", expected_sha256="0" * 64)


def test_mobilenet_v3_small_has_binary_output_when_torch_is_available() -> None:
    torch = pytest.importorskip("torch")
    try:
        __import__("torchvision")
    except (ImportError, RuntimeError) as error:
        pytest.skip(f"torchvision is unavailable: {error}")

    model = build_mobilenet_v3_small(weights="none")
    model.eval()
    with torch.no_grad():
        output = model(torch.zeros(1, 3, 224, 224))

    assert tuple(output.shape) == (1, 2)
