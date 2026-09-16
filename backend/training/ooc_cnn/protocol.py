"""Fail-closed access protocol for OoC CNN train, validation, and final evaluation."""

from __future__ import annotations

import fcntl
import json
import os
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any

from training.ooc_cnn.manifests import (
    ManifestData,
    ManifestSpec,
    SplitLock,
    assert_manifest_matches_spec,
    assert_manifests_group_disjoint,
    load_manifest,
    load_split_lock,
    relative_project_path,
    resolve_project_path,
    sha256_bytes,
    sha256_file,
    validate_sha256,
)

FINAL_EVAL_CONFIRMATION = "OPEN_FROZEN_TEST_ONCE"
REQUIRED_FROZEN_ARTIFACTS = frozenset(
    {"config", "train_validation_manifest", "test_manifest", "checkpoint"}
)
RECEIPT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")


class RunMode(StrEnum):
    SMOKE = "smoke"
    VALIDATION = "validation"
    FINAL_EVAL = "final-eval"


@dataclass(frozen=True)
class FrozenArtifact:
    name: str
    relative_path: str
    path: Path
    sha256: str


@dataclass(frozen=True)
class FrozenManifest:
    path: Path
    sha256: str
    experiment_id: str
    threshold: float
    artifacts: dict[str, FrozenArtifact]


@dataclass(frozen=True)
class RunManifests:
    mode: RunMode
    split_lock: SplitLock
    train_validation: ManifestData
    test: ManifestData | None
    frozen_manifest: FrozenManifest | None
    test_access_receipt: Path | None


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"{label} is not valid JSON") from error
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _parse_frozen_artifact(
    name: str, value: object, *, project_root: Path
) -> FrozenArtifact:
    if not isinstance(value, dict):
        raise ValueError(f"Frozen artifact {name} must be an object")
    relative_path = value.get("path")
    if not isinstance(relative_path, str):
        raise ValueError(f"Frozen artifact {name} path is invalid")
    return FrozenArtifact(
        name=name,
        relative_path=relative_path,
        path=resolve_project_path(project_root, relative_path, field=f"frozen artifact {name}"),
        sha256=validate_sha256(value.get("sha256"), f"frozen artifact {name} sha256"),
    )


def load_frozen_manifest(
    path: Path,
    *,
    project_root: Path,
    expected_sha256: str,
    deferred_artifacts: frozenset[str] = frozenset(),
) -> FrozenManifest:
    relative_project_path(project_root, path, field="frozen manifest path")
    expected_sha256 = validate_sha256(expected_sha256, "frozen manifest expected_sha256")
    actual_sha256 = sha256_file(path)
    if actual_sha256 != expected_sha256:
        raise ValueError("Frozen manifest checksum mismatch")
    value = _load_json(path, "Frozen manifest")
    if value.get("schema_version") != 1:
        raise ValueError("Frozen manifest must use schema_version 1")
    experiment_id = value.get("experiment_id")
    artifacts_value = value.get("artifacts")
    selection = value.get("selection")
    if not isinstance(experiment_id, str) or not experiment_id.strip():
        raise ValueError("Frozen manifest experiment_id is invalid")
    if not isinstance(artifacts_value, dict):
        raise ValueError("Frozen manifest artifacts are invalid")
    if not REQUIRED_FROZEN_ARTIFACTS <= set(artifacts_value):
        missing = sorted(REQUIRED_FROZEN_ARTIFACTS - set(artifacts_value))
        raise ValueError(f"Frozen manifest is missing artifacts: {', '.join(missing)}")
    if not isinstance(selection, dict):
        raise ValueError("Frozen manifest selection is invalid")
    threshold = selection.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, int | float):
        raise ValueError("Frozen manifest threshold is invalid")
    threshold = float(threshold)
    if not 0.0 <= threshold <= 1.0:
        raise ValueError("Frozen manifest threshold must be between zero and one")

    artifacts = {
        name: _parse_frozen_artifact(name, artifact, project_root=project_root)
        for name, artifact in artifacts_value.items()
    }
    for name, artifact in artifacts.items():
        if name in deferred_artifacts:
            continue
        if not artifact.path.is_file():
            raise ValueError(f"Frozen artifact is missing: {name}")
        if sha256_file(artifact.path) != artifact.sha256:
            raise ValueError(f"Frozen artifact checksum mismatch: {name}")
    return FrozenManifest(
        path=path.resolve(),
        sha256=actual_sha256,
        experiment_id=experiment_id.strip(),
        threshold=threshold,
        artifacts=artifacts,
    )


def _canonical_receipt_payload(receipt: dict[str, Any]) -> bytes:
    payload = {key: value for key, value in receipt.items() if key != "payload_sha256"}
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def validate_receipt_chain(receipt_directory: Path) -> tuple[Path, ...]:
    receipt_paths = tuple(sorted(receipt_directory.glob("[0-9]*.json")))
    previous_file_sha256: str | None = None
    for expected_sequence, path in enumerate(receipt_paths, 1):
        receipt = _load_json(path, "Test access receipt")
        if receipt.get("schema_version") != 1:
            raise ValueError(f"Test access receipt schema is invalid: {path}")
        if receipt.get("sequence") != expected_sequence:
            raise ValueError(f"Test access receipt sequence is invalid: {path}")
        if receipt.get("previous_receipt_sha256") != previous_file_sha256:
            raise ValueError(f"Test access receipt chain is broken: {path}")
        payload_sha256 = validate_sha256(
            receipt.get("payload_sha256"), "test access receipt payload_sha256"
        )
        if payload_sha256 != sha256_bytes(_canonical_receipt_payload(receipt)):
            raise ValueError(f"Test access receipt payload was modified: {path}")
        previous_file_sha256 = sha256_file(path)
    return receipt_paths


def append_test_access_receipt(
    *,
    receipt_directory: Path,
    project_root: Path,
    reason: str,
    frozen_manifest: FrozenManifest,
    test_spec: ManifestSpec,
    now: Callable[[], datetime] | None = None,
    receipt_id_factory: Callable[[], str] | None = None,
) -> Path:
    relative_project_path(project_root, receipt_directory, field="test access receipt directory")
    receipt_directory.mkdir(parents=True, exist_ok=True)
    lock_path = receipt_directory / ".chain.lock"
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        previous_paths = validate_receipt_chain(receipt_directory)
        previous_sha256 = sha256_file(previous_paths[-1]) if previous_paths else None
        receipt_id = (receipt_id_factory or (lambda: uuid.uuid4().hex))()
        if not RECEIPT_ID_PATTERN.fullmatch(receipt_id):
            raise ValueError("Test access receipt id is invalid")
        created_at = (now or (lambda: datetime.now(UTC)))()
        if created_at.tzinfo is None:
            raise ValueError("Test access receipt timestamp must be timezone-aware")
        created_at = created_at.astimezone(UTC)
        sequence = len(previous_paths) + 1
        receipt: dict[str, Any] = {
            "schema_version": 1,
            "sequence": sequence,
            "receipt_id": receipt_id,
            "event": "test_manifest_open_authorized",
            "created_at_utc": created_at.isoformat(),
            "mode": RunMode.FINAL_EVAL.value,
            "confirmation": FINAL_EVAL_CONFIRMATION,
            "reason": reason,
            "experiment_id": frozen_manifest.experiment_id,
            "selected_threshold": frozen_manifest.threshold,
            "frozen_manifest": {
                "path": relative_project_path(
                    project_root, frozen_manifest.path, field="frozen manifest"
                ),
                "sha256": frozen_manifest.sha256,
            },
            "test_manifest": {
                "path": test_spec.relative_path,
                "sha256": test_spec.sha256,
            },
            "previous_receipt_sha256": previous_sha256,
        }
        receipt["payload_sha256"] = sha256_bytes(_canonical_receipt_payload(receipt))
        timestamp = created_at.strftime("%Y%m%dT%H%M%S.%fZ")
        output_path = receipt_directory / f"{sequence:06d}-{timestamp}-{receipt_id}.json"
        output = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode("utf-8")
        with output_path.open("xb") as destination:
            destination.write(output)
            destination.flush()
            os.fsync(destination.fileno())
        return output_path


def _assert_frozen_matches_protocol(
    frozen: FrozenManifest,
    *,
    train_validation: ManifestData,
    train_validation_spec: ManifestSpec,
    test_spec: ManifestSpec,
) -> None:
    train_artifact = frozen.artifacts["train_validation_manifest"]
    test_artifact = frozen.artifacts["test_manifest"]
    if train_artifact.path != train_validation_spec.path:
        raise ValueError("Frozen train/validation manifest path does not match the split lock")
    if train_artifact.sha256 != train_validation.sha256:
        raise ValueError("Frozen train/validation manifest checksum does not match")
    if test_artifact.path != test_spec.path:
        raise ValueError("Frozen test manifest path does not match the split lock")
    if test_artifact.sha256 != test_spec.sha256:
        raise ValueError("Frozen test manifest checksum does not match the split lock")


def load_run_manifests(
    *,
    mode: RunMode | str,
    project_root: Path,
    split_lock_path: Path,
    train_validation_manifest_path: Path,
    split_lock_sha256: str | None = None,
    test_manifest_path: Path | None = None,
    frozen_manifest_path: Path | None = None,
    frozen_manifest_sha256: str | None = None,
    confirmation: str | None = None,
    test_open_reason: str | None = None,
    receipt_directory: Path | None = None,
    require_image_files: bool = False,
    verify_image_hashes: bool = False,
    now: Callable[[], datetime] | None = None,
    receipt_id_factory: Callable[[], str] | None = None,
) -> RunManifests:
    run_mode = RunMode(mode)
    root = project_root.resolve()
    relative_project_path(root, split_lock_path, field="split lock path")
    final_only_values = (
        test_manifest_path,
        frozen_manifest_path,
        frozen_manifest_sha256,
        confirmation,
        test_open_reason,
        receipt_directory,
    )
    if run_mode is not RunMode.FINAL_EVAL and any(value is not None for value in final_only_values):
        raise ValueError("Non-final modes cannot receive test access capabilities")
    if run_mode is RunMode.FINAL_EVAL:
        if confirmation != FINAL_EVAL_CONFIRMATION:
            raise ValueError("Final evaluation requires the exact test-open confirmation")
        if test_open_reason is None or len(test_open_reason.strip()) < 8:
            raise ValueError("Final evaluation requires a meaningful test-open reason")
        if any(
            value is None
            for value in (
                test_manifest_path,
                frozen_manifest_path,
                frozen_manifest_sha256,
                receipt_directory,
            )
        ):
            raise ValueError(
                "Final evaluation requires test, frozen manifest, hash, and receipt path"
            )

    split_lock = load_split_lock(
        split_lock_path, project_root=root, expected_sha256=split_lock_sha256
    )
    train_validation_path = train_validation_manifest_path.resolve()
    if train_validation_path != split_lock.train_validation.path:
        raise ValueError("Train/validation manifest path does not match the split lock")
    train_validation = load_manifest(
        train_validation_path,
        project_root=root,
        expected_sha256=split_lock.train_validation.sha256,
        allowed_splits=frozenset({"train", "validation"}),
        required_splits=frozenset({"train", "validation"}),
        require_image_files=require_image_files,
        verify_image_hashes=verify_image_hashes,
    )
    assert_manifest_matches_spec(train_validation, split_lock.train_validation)
    if run_mode is not RunMode.FINAL_EVAL:
        return RunManifests(
            mode=run_mode,
            split_lock=split_lock,
            train_validation=train_validation,
            test=None,
            frozen_manifest=None,
            test_access_receipt=None,
        )

    assert test_manifest_path is not None
    assert frozen_manifest_path is not None
    assert frozen_manifest_sha256 is not None
    assert test_open_reason is not None
    assert receipt_directory is not None
    test_path = test_manifest_path.resolve()
    if test_path != split_lock.test.path:
        raise ValueError("Test manifest path does not match the split lock")
    frozen = load_frozen_manifest(
        frozen_manifest_path,
        project_root=root,
        expected_sha256=frozen_manifest_sha256,
        deferred_artifacts=frozenset({"test_manifest"}),
    )
    _assert_frozen_matches_protocol(
        frozen,
        train_validation=train_validation,
        train_validation_spec=split_lock.train_validation,
        test_spec=split_lock.test,
    )
    receipt = append_test_access_receipt(
        receipt_directory=receipt_directory,
        project_root=root,
        reason=test_open_reason.strip(),
        frozen_manifest=frozen,
        test_spec=split_lock.test,
        now=now,
        receipt_id_factory=receipt_id_factory,
    )
    test = load_manifest(
        test_path,
        project_root=root,
        expected_sha256=split_lock.test.sha256,
        allowed_splits=frozenset({"test"}),
        required_splits=frozenset({"test"}),
        require_image_files=require_image_files,
        verify_image_hashes=verify_image_hashes,
    )
    assert_manifest_matches_spec(test, split_lock.test)
    assert_manifests_group_disjoint(train_validation, test)
    return RunManifests(
        mode=run_mode,
        split_lock=split_lock,
        train_validation=train_validation,
        test=test,
        frozen_manifest=frozen,
        test_access_receipt=receipt,
    )
