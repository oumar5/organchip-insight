"""Build the deterministic image-only BBBC038 instance-benchmark subset."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET_ROOT = PROJECT_ROOT / "data/raw/bbbc038/stage1_train"
DEFAULT_ARCHIVE = PROJECT_ROOT / "data/raw/bbbc038/stage1_train.zip"
DEFAULT_OUTPUT = PROJECT_ROOT / "data/manifests/bbbc038-stage1-subset-v1.json"
EXPECTED_ARCHIVE_SHA256 = "dcb6edc2690f137406638b2309581a71522c4dff19157d118453b448dcddcb68"


@dataclass(frozen=True, slots=True)
class ImageInventoryRow:
    image_id: str
    image_path: str
    mode: str
    width: int
    height: int
    grayscale_mean: float
    grayscale_std: float


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inventory_images(dataset_root: Path, project_root: Path) -> list[ImageInventoryRow]:
    rows: list[ImageInventoryRow] = []
    for image_dir in sorted(path for path in dataset_root.iterdir() if path.is_dir()):
        image_path = image_dir / "images" / f"{image_dir.name}.png"
        if not image_path.is_file():
            raise FileNotFoundError(f"Missing BBBC038 image: {image_path}")
        with Image.open(image_path) as source:
            source.load()
            grayscale = np.asarray(source.convert("L"), dtype=np.float32) / 255.0
            rows.append(
                ImageInventoryRow(
                    image_id=image_dir.name,
                    image_path=str(image_path.relative_to(project_root)),
                    mode=source.mode,
                    width=source.width,
                    height=source.height,
                    grayscale_mean=round(float(grayscale.mean()), 8),
                    grayscale_std=round(float(grayscale.std()), 8),
                )
            )
    if not rows:
        raise FileNotFoundError(f"No BBBC038 image directories found in {dataset_root}")
    return rows


def select_diverse_images(
    rows: list[ImageInventoryRow],
    *,
    extra_extremes: int = 3,
) -> list[tuple[ImageInventoryRow, str]]:
    """Select one representative per resolution, then distinct appearance extremes."""
    if not rows:
        raise ValueError("BBBC038 inventory must not be empty")
    by_resolution: dict[tuple[int, int], list[ImageInventoryRow]] = defaultdict(list)
    for row in rows:
        by_resolution[(row.width, row.height)].append(row)

    selected: list[tuple[ImageInventoryRow, str]] = []
    selected_ids: set[str] = set()
    mean_scale = max(row.grayscale_mean for row in rows) - min(
        row.grayscale_mean for row in rows
    )
    std_scale = max(row.grayscale_std for row in rows) - min(
        row.grayscale_std for row in rows
    )
    mean_scale = mean_scale or 1.0
    std_scale = std_scale or 1.0

    for resolution, candidates in sorted(by_resolution.items()):
        median_mean = float(np.median([row.grayscale_mean for row in candidates]))
        median_std = float(np.median([row.grayscale_std for row in candidates]))
        representative = min(
            candidates,
            key=lambda row: (
                abs(row.grayscale_mean - median_mean) / mean_scale
                + abs(row.grayscale_std - median_std) / std_scale,
                row.image_id,
            ),
        )
        selected.append(
            (representative, f"resolution-representative-{resolution[0]}x{resolution[1]}")
        )
        selected_ids.add(representative.image_id)

    extreme_rankings = (
        (
            "lowest-grayscale-mean",
            sorted(rows, key=lambda row: (row.grayscale_mean, row.image_id)),
        ),
        (
            "highest-grayscale-mean",
            sorted(rows, key=lambda row: (-row.grayscale_mean, row.image_id)),
        ),
        (
            "highest-grayscale-std",
            sorted(rows, key=lambda row: (-row.grayscale_std, row.image_id)),
        ),
    )
    for reason, ranking in extreme_rankings[:extra_extremes]:
        candidate = next(row for row in ranking if row.image_id not in selected_ids)
        selected.append((candidate, reason))
        selected_ids.add(candidate.image_id)
    return selected


def masks_tree_record(mask_dir: Path, project_root: Path) -> tuple[int, str]:
    mask_paths = sorted(mask_dir.glob("*.png"))
    if not mask_paths:
        raise FileNotFoundError(f"No BBBC038 instance masks found in {mask_dir}")
    digest = hashlib.sha256()
    for mask_path in mask_paths:
        relative = str(mask_path.relative_to(project_root))
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        digest.update(sha256_file(mask_path).encode("ascii"))
        digest.update(b"\n")
    return len(mask_paths), digest.hexdigest()


def build_manifest(
    *,
    dataset_root: Path,
    archive_path: Path,
    project_root: Path,
) -> dict[str, Any]:
    archive_sha256 = sha256_file(archive_path)
    if archive_sha256 != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("BBBC038 archive SHA-256 does not match the registered resource")
    rows = inventory_images(dataset_root, project_root)
    selected = select_diverse_images(rows)
    if len(selected) != 12:
        raise ValueError(f"Expected 12 pre-registered BBBC038 images, got {len(selected)}")

    entries: list[dict[str, Any]] = []
    for row, reason in selected:
        image_path = project_root / row.image_path
        mask_dir = dataset_root / row.image_id / "masks"
        truth_count, masks_sha256 = masks_tree_record(mask_dir, project_root)
        entries.append(
            {
                **asdict(row),
                "selection_reason": reason,
                "image_sha256": sha256_file(image_path),
                "masks_dir": str(mask_dir.relative_to(project_root)),
                "truth_instance_count": truth_count,
                "masks_tree_sha256": masks_sha256,
            }
        )

    resolution_counts = Counter(f"{row.width}x{row.height}" for row in rows)
    return {
        "schema_version": 1,
        "subset_id": "bbbc038-stage1-image-only-diversity-v1",
        "dataset": {
            "id": "BBBC038v1-stage1-train",
            "source": "https://bbbc.broadinstitute.org/BBBC038",
            "license": "CC0-1.0",
            "archive_path": str(archive_path.relative_to(project_root)),
            "archive_sha256": archive_sha256,
            "inventory_image_count": len(rows),
        },
        "selection_policy": {
            "uses_ground_truth_for_selection": False,
            "description": (
                "One image-only median representative per exact resolution, then the "
                "three distinct grayscale appearance extremes: minimum mean, maximum "
                "mean, maximum standard deviation. Ties use the image id."
            ),
            "features": [
                "source width",
                "source height",
                "grayscale mean",
                "grayscale standard deviation",
            ],
            "selection_count": len(entries),
        },
        "inventory_summary": {
            "modes": dict(sorted(Counter(row.mode for row in rows).items())),
            "resolutions": dict(sorted(resolution_counts.items())),
        },
        "images": entries,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=DEFAULT_DATASET_ROOT)
    parser.add_argument("--archive", type=Path, default=DEFAULT_ARCHIVE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    manifest = build_manifest(
        dataset_root=arguments.dataset_root.resolve(),
        archive_path=arguments.archive.resolve(),
        project_root=PROJECT_ROOT,
    )
    serialized = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if arguments.check:
        if not arguments.output.is_file() or arguments.output.read_text(
            encoding="utf-8"
        ) != serialized:
            raise SystemExit("BBBC038 subset manifest is not synchronized")
        print(f"OK: {arguments.output}")
        return
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(serialized, encoding="utf-8")
    print(f"Wrote {arguments.output} ({len(manifest['images'])} images)")


if __name__ == "__main__":
    main()
