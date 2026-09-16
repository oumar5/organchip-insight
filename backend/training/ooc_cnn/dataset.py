"""Image access and deterministic smoke sampling for validated manifests."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from PIL import Image

from training.ooc_cnn.manifests import ManifestRecord, resolve_project_path, sha256_file
from training.ooc_cnn.preprocessing import force_rgb

SplitName = Literal["train", "validation", "test"]
SMOKE_SPLITS: tuple[SplitName, ...] = ("train", "validation")


def resolve_record_path(
    record: ManifestRecord,
    project_root: Path,
    *,
    require_file: bool = True,
) -> Path:
    """Resolve a manifest path while rejecting traversal and escaping symlinks."""
    candidate = resolve_project_path(
        project_root,
        record.path,
        field="manifest image path",
    )
    if require_file and not candidate.is_file():
        raise FileNotFoundError(f"manifest image is missing: {record.path}")
    return candidate


class ManifestImageDataset:
    """PyTorch-compatible dataset that remains importable without PyTorch."""

    def __init__(
        self,
        records: Sequence[ManifestRecord],
        project_root: Path,
        *,
        transform: Callable[[Image.Image], Any] | None = None,
        verify_hashes: bool = False,
    ) -> None:
        self.records = tuple(records)
        if not self.records:
            raise ValueError("manifest dataset must contain at least one record")
        self.project_root = project_root.resolve(strict=True)
        self.transform = transform
        self.paths = tuple(
            resolve_record_path(record, self.project_root) for record in self.records
        )
        if verify_hashes:
            for record, path in zip(self.records, self.paths, strict=True):
                if sha256_file(path) != record.sha256:
                    raise ValueError(f"image checksum mismatch: {record.path}")

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> tuple[Any, int]:
        record = self.records[index]
        with Image.open(self.paths[index]) as source:
            image = force_rgb(source).copy()
        transformed = self.transform(image) if self.transform is not None else image
        return transformed, record.target_index

    def record_at(self, index: int) -> ManifestRecord:
        return self.records[index]


def select_smoke_records(
    records: Iterable[ManifestRecord],
    *,
    seed: int,
    samples_per_stratum: int = 1,
    splits: Sequence[SplitName] = SMOKE_SPLITS,
    max_records_by_split: Mapping[str, int] | None = None,
) -> list[ManifestRecord]:
    """Select deterministically within each split/label/acquisition-group stratum."""
    if samples_per_stratum <= 0:
        raise ValueError("samples_per_stratum must be positive")
    selected_splits = tuple(splits)
    if not selected_splits or len(set(selected_splits)) != len(selected_splits):
        raise ValueError("splits must contain unique train/validation entries")
    if any(split not in SMOKE_SPLITS for split in selected_splits):
        raise ValueError("smoke sampling is restricted to train and validation")
    if max_records_by_split is not None:
        if set(max_records_by_split) != set(selected_splits):
            raise ValueError("smoke limits must define every selected split exactly once")
        if any(
            isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0
            for limit in max_records_by_split.values()
        ):
            raise ValueError("smoke limits must be positive integers")

    strata: dict[tuple[str, str, str], list[ManifestRecord]] = defaultdict(list)
    for record in records:
        if record.grouped_split in selected_splits:
            key = (
                record.grouped_split,
                record.target_label,
                record.acquisition_prefix,
            )
            strata[key].append(record)

    def stable_rank(record: ManifestRecord) -> tuple[str, str]:
        payload = f"{seed}\0{record.path}\0{record.sha256}".encode()
        return hashlib.sha256(payload).hexdigest(), record.path

    candidates_by_split: dict[str, dict[str, list[ManifestRecord]]] = {}
    for split in selected_splits:
        candidates_by_label: dict[str, list[ManifestRecord]] = {
            "bad": [],
            "good": [],
        }
        for key, values in strata.items():
            key_split, label, _group = key
            if key_split == split:
                candidates_by_label[label].extend(
                    sorted(values, key=stable_rank)[:samples_per_stratum]
                )
        if any(not candidates_by_label[label] for label in ("bad", "good")):
            raise ValueError(f"smoke split {split} must contain both target classes")
        for label in candidates_by_label:
            candidates_by_label[label].sort(key=stable_rank)
        candidates_by_split[split] = candidates_by_label

    selected: list[ManifestRecord] = []
    for split in selected_splits:
        queues = candidates_by_split[split]
        available = sum(len(queue) for queue in queues.values())
        limit = (
            min(max_records_by_split[split], available)
            if max_records_by_split is not None
            else available
        )
        selected_groups: set[str] = set()
        while limit > 0 and any(queues.values()):
            for label in ("bad", "good"):
                queue = queues[label]
                if not queue or limit == 0:
                    continue
                candidate_index = next(
                    (
                        index
                        for index, candidate in enumerate(queue)
                        if candidate.acquisition_prefix not in selected_groups
                    ),
                    0,
                )
                candidate = queue.pop(candidate_index)
                selected.append(candidate)
                selected_groups.add(candidate.acquisition_prefix)
                limit -= 1
    return selected
