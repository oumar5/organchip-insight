"""Build and validate physically separated OoC CNN manifests."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from typing import Any

CANONICAL_SPLIT_SHA256 = "5ffcf7ff0d69901f7362903d2532462c2758386dfbee2d6265b7a11d61b30d8c"
MANIFEST_COLUMNS = (
    "path",
    "image_id",
    "acquisition_prefix",
    "grouped_split",
    "target_label",
    "target_index",
    "cell_type",
    "day_bucket",
    "published_split",
    "sha256",
)
VALID_SPLITS = frozenset({"train", "validation", "test"})
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class ManifestRecord:
    path: str
    image_id: str
    acquisition_prefix: str
    grouped_split: str
    target_label: str
    target_index: int
    cell_type: str
    day_bucket: str
    published_split: str
    sha256: str


@dataclass(frozen=True)
class ManifestData:
    path: Path
    sha256: str
    records: tuple[ManifestRecord, ...]
    split_counts: dict[str, int]
    groups_by_split: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class ManifestSpec:
    role: str
    relative_path: str
    path: Path
    sha256: str
    rows: int
    split_counts: dict[str, int]
    groups_by_split: dict[str, tuple[str, ...]]


@dataclass(frozen=True)
class SplitLock:
    path: Path
    sha256: str
    split_id: str
    source_relative_path: str
    source_sha256: str
    train_validation: ManifestSpec
    test: ManifestSpec


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA256_PATTERN.fullmatch(value):
        raise ValueError(f"{field} must be a lowercase SHA-256 digest")
    return value


def resolve_project_path(project_root: Path, value: str, *, field: str) -> Path:
    if not value or value != value.strip() or "\\" in value:
        raise ValueError(f"{field} must be a non-empty normalized POSIX path")
    pure_path = PurePosixPath(value)
    if pure_path.is_absolute() or any(part in {"", ".", ".."} for part in pure_path.parts):
        raise ValueError(f"{field} must stay inside the project root")
    root = project_root.resolve()
    candidate = root.joinpath(*pure_path.parts).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{field} escapes the project root") from error
    return candidate


def relative_project_path(project_root: Path, path: Path, *, field: str) -> str:
    root = project_root.resolve()
    candidate = path.resolve()
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise ValueError(f"{field} must stay inside the project root") from error
    if not relative.parts:
        raise ValueError(f"{field} cannot be the project root")
    return relative.as_posix()


def _parse_record(row: dict[str, str], row_number: int) -> ManifestRecord:
    missing_values = [column for column in MANIFEST_COLUMNS if not row.get(column, "").strip()]
    if missing_values:
        raise ValueError(
            f"Manifest row {row_number} has empty fields: {', '.join(missing_values)}"
        )
    split = row["grouped_split"]
    if split not in VALID_SPLITS:
        raise ValueError(f"Manifest row {row_number} has an unknown grouped_split: {split}")
    label = row["target_label"]
    expected_target = {"bad": 0, "good": 1}.get(label)
    if expected_target is None:
        raise ValueError(f"Manifest row {row_number} has an unknown target_label: {label}")
    try:
        target_index = int(row["target_index"])
    except ValueError as error:
        raise ValueError(f"Manifest row {row_number} has an invalid target_index") from error
    if target_index != expected_target:
        raise ValueError(f"Manifest row {row_number} target label/index mapping is inconsistent")
    return ManifestRecord(
        path=row["path"],
        image_id=row["image_id"],
        acquisition_prefix=row["acquisition_prefix"],
        grouped_split=split,
        target_label=label,
        target_index=target_index,
        cell_type=row["cell_type"],
        day_bucket=row["day_bucket"],
        published_split=row["published_split"],
        sha256=validate_sha256(row["sha256"], f"row {row_number} sha256"),
    )


def _summaries(
    records: Iterable[ManifestRecord],
) -> tuple[dict[str, int], dict[str, tuple[str, ...]]]:
    record_list = tuple(records)
    split_counts = dict(sorted(Counter(record.grouped_split for record in record_list).items()))
    groups_by_split = {
        split: tuple(
            sorted(
                record.acquisition_prefix
                for record in record_list
                if record.grouped_split == split
            )
        )
        for split in sorted(split_counts)
    }
    groups_by_split = {
        split: tuple(dict.fromkeys(groups)) for split, groups in groups_by_split.items()
    }
    return split_counts, groups_by_split


def _assert_group_disjoint(groups_by_split: dict[str, tuple[str, ...]]) -> None:
    split_names = sorted(groups_by_split)
    for left_index, left_name in enumerate(split_names):
        left_groups = set(groups_by_split[left_name])
        for right_name in split_names[left_index + 1 :]:
            overlap = sorted(left_groups & set(groups_by_split[right_name]))
            if overlap:
                raise ValueError(
                    f"Acquisition groups cross {left_name}/{right_name}: {', '.join(overlap)}"
                )


def load_manifest(
    path: Path,
    *,
    project_root: Path,
    expected_sha256: str,
    allowed_splits: frozenset[str],
    required_splits: frozenset[str],
    image_root: Path | None = None,
    require_image_files: bool = False,
    verify_image_hashes: bool = False,
) -> ManifestData:
    relative_project_path(project_root, path, field="manifest path")
    resolved_image_root = (image_root or project_root).resolve()
    if not resolved_image_root.is_dir():
        raise ValueError("Manifest image root is missing or not a directory")
    expected_sha256 = validate_sha256(expected_sha256, "manifest expected_sha256")
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ValueError(f"Manifest checksum mismatch: {path}")
    with path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != MANIFEST_COLUMNS:
            raise ValueError(f"Manifest columns or order are invalid: {path}")
        records = tuple(_parse_record(row, row_number) for row_number, row in enumerate(reader, 2))
    if not records:
        raise ValueError(f"Manifest is empty: {path}")

    observed_splits = {record.grouped_split for record in records}
    if not observed_splits <= allowed_splits:
        unexpected = sorted(observed_splits - allowed_splits)
        raise ValueError(f"Manifest contains forbidden splits: {', '.join(unexpected)}")
    if not required_splits <= observed_splits:
        missing = sorted(required_splits - observed_splits)
        raise ValueError(f"Manifest is missing required splits: {', '.join(missing)}")

    seen_paths: set[str] = set()
    seen_image_ids: set[str] = set()
    seen_resolved_paths: set[Path] = set()
    hash_splits: dict[str, set[str]] = defaultdict(set)
    for record in records:
        if record.path in seen_paths:
            raise ValueError(f"Manifest contains a duplicate path: {record.path}")
        seen_paths.add(record.path)
        if record.image_id in seen_image_ids:
            raise ValueError(f"Manifest contains a duplicate image_id: {record.image_id}")
        seen_image_ids.add(record.image_id)
        hash_splits[record.sha256].add(record.grouped_split)
        resolved = resolve_project_path(
            resolved_image_root,
            record.path,
            field="manifest image path",
        )
        if resolved in seen_resolved_paths:
            raise ValueError(f"Manifest paths collide after normalization: {record.path}")
        seen_resolved_paths.add(resolved)
        if (require_image_files or verify_image_hashes) and not resolved.is_file():
            raise ValueError(f"Manifest image is missing or not a file: {record.path}")
        if verify_image_hashes and sha256_file(resolved) != record.sha256:
            raise ValueError(f"Manifest image checksum mismatch: {record.path}")

    crossing_hashes = sorted(sha256 for sha256, splits in hash_splits.items() if len(splits) > 1)
    if crossing_hashes:
        raise ValueError("Exact image hashes cross grouped splits")

    split_counts, groups_by_split = _summaries(records)
    _assert_group_disjoint(groups_by_split)
    return ManifestData(
        path=path.resolve(),
        sha256=actual_sha256,
        records=records,
        split_counts=split_counts,
        groups_by_split=groups_by_split,
    )


def _records_to_csv_bytes(records: Iterable[ManifestRecord]) -> bytes:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for record in records:
        writer.writerow(asdict(record))
    return output.getvalue().encode("utf-8")


def _manifest_lock_entry(
    project_root: Path,
    path: Path,
    content: bytes,
    records: tuple[ManifestRecord, ...],
) -> dict[str, Any]:
    split_counts, groups_by_split = _summaries(records)
    return {
        "path": relative_project_path(project_root, path, field="output manifest"),
        "sha256": sha256_bytes(content),
        "rows": len(records),
        "split_counts": split_counts,
        "groups": {split: list(groups) for split, groups in groups_by_split.items()},
    }


def _write_if_changed(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() == content:
        return
    path.write_bytes(content)


def build_separated_manifests(
    *,
    project_root: Path,
    source_path: Path,
    expected_source_sha256: str,
    train_validation_path: Path,
    test_path: Path,
    lock_path: Path,
    split_id: str = "ooc-grouped-by-acquisition-prefix-v1",
) -> dict[str, Any]:
    root = project_root.resolve()
    paths = {
        "source": source_path.resolve(),
        "train_validation": train_validation_path.resolve(),
        "test": test_path.resolve(),
        "lock": lock_path.resolve(),
    }
    for name, path in paths.items():
        relative_project_path(root, path, field=name)
    if len(set(paths.values())) != len(paths):
        raise ValueError("Source, output manifests, and lock must use distinct paths")

    source = load_manifest(
        paths["source"],
        project_root=root,
        expected_sha256=expected_source_sha256,
        allowed_splits=VALID_SPLITS,
        required_splits=VALID_SPLITS,
    )
    train_validation_records = tuple(
        record for record in source.records if record.grouped_split in {"train", "validation"}
    )
    test_records = tuple(record for record in source.records if record.grouped_split == "test")
    train_validation_bytes = _records_to_csv_bytes(train_validation_records)
    test_bytes = _records_to_csv_bytes(test_records)
    train_validation_entry = _manifest_lock_entry(
        root, paths["train_validation"], train_validation_bytes, train_validation_records
    )
    test_entry = _manifest_lock_entry(root, paths["test"], test_bytes, test_records)
    all_groups = {
        **{
            f"train_validation:{key}": value
            for key, value in source.groups_by_split.items()
            if key != "test"
        },
        "test:test": source.groups_by_split["test"],
    }
    _assert_group_disjoint(all_groups)

    lock: dict[str, Any] = {
        "schema_version": 1,
        "split_id": split_id,
        "source": {
            "path": relative_project_path(root, paths["source"], field="source"),
            "sha256": source.sha256,
            "rows": len(source.records),
        },
        "manifests": {
            "train_validation": train_validation_entry,
            "test": test_entry,
        },
        "group_overlaps": {
            "train_validation": [],
            "train_test": [],
            "validation_test": [],
        },
    }
    lock_bytes = (json.dumps(lock, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _write_if_changed(paths["train_validation"], train_validation_bytes)
    _write_if_changed(paths["test"], test_bytes)
    _write_if_changed(paths["lock"], lock_bytes)
    return lock


def _parse_manifest_spec(
    role: str, value: object, *, project_root: Path
) -> ManifestSpec:
    if not isinstance(value, dict):
        raise ValueError(f"Split lock manifest {role} must be an object")
    relative_path = value.get("path")
    if not isinstance(relative_path, str):
        raise ValueError(f"Split lock manifest {role} path is invalid")
    path = resolve_project_path(project_root, relative_path, field=f"{role} manifest path")
    sha256 = validate_sha256(value.get("sha256"), f"{role} manifest sha256")
    rows = value.get("rows")
    if not isinstance(rows, int) or isinstance(rows, bool) or rows <= 0:
        raise ValueError(f"Split lock manifest {role} rows must be positive")
    split_counts_value = value.get("split_counts")
    groups_value = value.get("groups")
    if not isinstance(split_counts_value, dict) or not isinstance(groups_value, dict):
        raise ValueError(f"Split lock manifest {role} summaries are invalid")
    split_counts: dict[str, int] = {}
    groups_by_split: dict[str, tuple[str, ...]] = {}
    for split, count in split_counts_value.items():
        invalid_count = not isinstance(count, int) or isinstance(count, bool) or count <= 0
        if split not in VALID_SPLITS or invalid_count:
            raise ValueError(f"Split lock manifest {role} has invalid split counts")
        split_counts[split] = count
    for split, groups in groups_value.items():
        if split not in VALID_SPLITS or not isinstance(groups, list) or not groups:
            raise ValueError(f"Split lock manifest {role} has invalid groups")
        if not all(isinstance(group, str) and group for group in groups):
            raise ValueError(f"Split lock manifest {role} has invalid group values")
        if len(groups) != len(set(groups)):
            raise ValueError(f"Split lock manifest {role} has duplicate groups")
        groups_by_split[split] = tuple(groups)
    if set(split_counts) != set(groups_by_split) or sum(split_counts.values()) != rows:
        raise ValueError(f"Split lock manifest {role} summaries are inconsistent")
    return ManifestSpec(
        role=role,
        relative_path=relative_path,
        path=path,
        sha256=sha256,
        rows=rows,
        split_counts=dict(sorted(split_counts.items())),
        groups_by_split={key: tuple(value) for key, value in sorted(groups_by_split.items())},
    )


def load_split_lock(
    path: Path, *, project_root: Path, expected_sha256: str | None = None
) -> SplitLock:
    relative_project_path(project_root, path, field="split lock path")
    actual_sha256 = sha256_file(path)
    if expected_sha256 is not None and actual_sha256 != validate_sha256(
        expected_sha256, "split lock expected_sha256"
    ):
        raise ValueError("Split lock checksum mismatch")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("Split lock is not valid JSON") from error
    if not isinstance(value, dict) or value.get("schema_version") != 1:
        raise ValueError("Split lock must use schema_version 1")
    split_id = value.get("split_id")
    source = value.get("source")
    manifests = value.get("manifests")
    if not isinstance(split_id, str) or not split_id:
        raise ValueError("Split lock split_id is invalid")
    if not isinstance(source, dict) or not isinstance(manifests, dict):
        raise ValueError("Split lock source or manifests are invalid")
    source_relative_path = source.get("path")
    if not isinstance(source_relative_path, str):
        raise ValueError("Split lock source path is invalid")
    resolve_project_path(project_root, source_relative_path, field="split lock source path")
    source_sha256 = validate_sha256(source.get("sha256"), "split lock source sha256")
    source_rows = source.get("rows")
    if not isinstance(source_rows, int) or isinstance(source_rows, bool) or source_rows <= 0:
        raise ValueError("Split lock source rows are invalid")
    if set(manifests) != {"train_validation", "test"}:
        raise ValueError("Split lock must contain train_validation and test manifests")
    train_validation = _parse_manifest_spec(
        "train_validation", manifests["train_validation"], project_root=project_root
    )
    test = _parse_manifest_spec("test", manifests["test"], project_root=project_root)
    if set(train_validation.split_counts) != {"train", "validation"}:
        raise ValueError("Train/validation manifest specification has invalid splits")
    if set(test.split_counts) != {"test"}:
        raise ValueError("Test manifest specification has invalid splits")
    if source_rows != train_validation.rows + test.rows:
        raise ValueError("Split lock source and manifest row counts are inconsistent")
    combined_groups = {**train_validation.groups_by_split, **test.groups_by_split}
    _assert_group_disjoint(combined_groups)
    overlaps = value.get("group_overlaps")
    expected_overlap_keys = {"train_validation", "train_test", "validation_test"}
    if (
        not isinstance(overlaps, dict)
        or set(overlaps) != expected_overlap_keys
        or any(overlap != [] for overlap in overlaps.values())
    ):
        raise ValueError("Split lock declares group overlap")
    return SplitLock(
        path=path.resolve(),
        sha256=actual_sha256,
        split_id=split_id,
        source_relative_path=source_relative_path,
        source_sha256=source_sha256,
        train_validation=train_validation,
        test=test,
    )


def assert_manifest_matches_spec(manifest: ManifestData, spec: ManifestSpec) -> None:
    if manifest.path != spec.path:
        raise ValueError(f"{spec.role} manifest path does not match the split lock")
    if manifest.sha256 != spec.sha256:
        raise ValueError(f"{spec.role} manifest checksum does not match the split lock")
    if len(manifest.records) != spec.rows:
        raise ValueError(f"{spec.role} manifest row count does not match the split lock")
    if manifest.split_counts != spec.split_counts:
        raise ValueError(f"{spec.role} manifest split counts do not match the split lock")
    if manifest.groups_by_split != spec.groups_by_split:
        raise ValueError(f"{spec.role} manifest groups do not match the split lock")


def assert_manifests_group_disjoint(*manifests: ManifestData) -> None:
    groups_by_split: dict[str, tuple[str, ...]] = {}
    seen_paths: set[str] = set()
    seen_image_ids: set[str] = set()
    seen_hashes: set[str] = set()
    for manifest in manifests:
        paths = {record.path for record in manifest.records}
        image_ids = {record.image_id for record in manifest.records}
        hashes = {record.sha256 for record in manifest.records}
        if seen_paths & paths:
            raise ValueError("Image paths cross physical manifests")
        if seen_image_ids & image_ids:
            raise ValueError("Image ids cross physical manifests")
        if seen_hashes & hashes:
            raise ValueError("Exact image hashes cross physical manifests")
        seen_paths.update(paths)
        seen_image_ids.update(image_ids)
        seen_hashes.update(hashes)
        for split, groups in manifest.groups_by_split.items():
            if split in groups_by_split:
                raise ValueError(f"Split is present in more than one manifest: {split}")
            groups_by_split[split] = groups
    _assert_group_disjoint(groups_by_split)
