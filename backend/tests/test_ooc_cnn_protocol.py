import builtins
import csv
import importlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from training.ooc_cnn.manifests import (
    MANIFEST_COLUMNS,
    build_separated_manifests,
    sha256_file,
)
from training.ooc_cnn.protocol import (
    FINAL_EVAL_CONFIRMATION,
    RunMode,
    load_run_manifests,
    validate_receipt_chain,
)


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=MANIFEST_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fixture_project(tmp_path: Path) -> dict[str, Path]:
    rows: list[dict[str, str]] = []
    for index, (split, group, label) in enumerate(
        [
            ("train", "group-train", "bad"),
            ("train", "group-train", "good"),
            ("validation", "group-validation", "bad"),
            ("validation", "group-validation", "good"),
            ("test", "group-test", "bad"),
            ("test", "group-test", "good"),
        ]
    ):
        image_path = tmp_path / "data/raw/ooc" / f"image-{index}.png"
        image_path.parent.mkdir(parents=True, exist_ok=True)
        image_path.write_bytes(f"image-{index}".encode())
        rows.append(
            {
                "path": image_path.relative_to(tmp_path).as_posix(),
                "image_id": f"image-{index}",
                "acquisition_prefix": group,
                "grouped_split": split,
                "target_label": label,
                "target_index": "1" if label == "good" else "0",
                "cell_type": "A549",
                "day_bucket": "0-1_days",
                "published_split": "train",
                "sha256": sha256_file(image_path),
            }
        )
    source = tmp_path / "data/splits/source.csv"
    train_validation = tmp_path / "data/splits/train-validation.csv"
    test = tmp_path / "data/splits/test.csv"
    lock = tmp_path / "data/splits/lock.json"
    _write_csv(source, rows)
    build_separated_manifests(
        project_root=tmp_path,
        source_path=source,
        expected_source_sha256=sha256_file(source),
        train_validation_path=train_validation,
        test_path=test,
        lock_path=lock,
        split_id="fixture-split",
    )
    return {
        "root": tmp_path,
        "source": source,
        "train_validation": train_validation,
        "test": test,
        "lock": lock,
    }


def _write_frozen_manifest(paths: dict[str, Path]) -> Path:
    config = paths["root"] / "data/experiments/config.json"
    checkpoint = paths["root"] / "data/experiments/checkpoint.bin"
    config.parent.mkdir(parents=True, exist_ok=True)
    config.write_text('{"model":"fixture"}\n', encoding="utf-8")
    checkpoint.write_bytes(b"checkpoint")
    frozen = paths["root"] / "data/experiments/frozen.json"
    frozen.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "experiment_id": "fixture-cnn-v1",
                "selection": {"threshold": 0.55},
                "artifacts": {
                    "config": {
                        "path": config.relative_to(paths["root"]).as_posix(),
                        "sha256": sha256_file(config),
                    },
                    "checkpoint": {
                        "path": checkpoint.relative_to(paths["root"]).as_posix(),
                        "sha256": sha256_file(checkpoint),
                    },
                    "train_validation_manifest": {
                        "path": paths["train_validation"].relative_to(paths["root"]).as_posix(),
                        "sha256": sha256_file(paths["train_validation"]),
                    },
                    "test_manifest": {
                        "path": paths["test"].relative_to(paths["root"]).as_posix(),
                        "sha256": sha256_file(paths["test"]),
                    },
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return frozen


def test_build_manifests_preserves_frozen_split_exactly(tmp_path: Path) -> None:
    paths = _fixture_project(tmp_path)
    source_before = paths["source"].read_bytes()
    outputs_before = {
        name: paths[name].read_bytes() for name in ("train_validation", "test", "lock")
    }

    build_separated_manifests(
        project_root=tmp_path,
        source_path=paths["source"],
        expected_source_sha256=sha256_file(paths["source"]),
        train_validation_path=paths["train_validation"],
        test_path=paths["test"],
        lock_path=paths["lock"],
        split_id="fixture-split",
    )

    assert paths["source"].read_bytes() == source_before
    assert {
        name: paths[name].read_bytes() for name in ("train_validation", "test", "lock")
    } == outputs_before
    lock = json.loads(paths["lock"].read_text(encoding="utf-8"))
    assert lock["source"]["rows"] == 6
    assert lock["manifests"]["train_validation"]["rows"] == 4
    assert lock["manifests"]["test"]["rows"] == 2
    assert lock["group_overlaps"] == {
        "train_test": [],
        "train_validation": [],
        "validation_test": [],
    }


def test_manifest_generation_rejects_exact_hash_crossing_splits(tmp_path: Path) -> None:
    paths = _fixture_project(tmp_path)
    with paths["source"].open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    rows[-1]["sha256"] = rows[0]["sha256"]
    _write_csv(paths["source"], rows)
    new_train_validation = tmp_path / "data/splits/new-train-validation.csv"
    new_test = tmp_path / "data/splits/new-test.csv"
    new_lock = tmp_path / "data/splits/new-lock.json"

    with pytest.raises(ValueError, match="hashes cross grouped splits"):
        build_separated_manifests(
            project_root=tmp_path,
            source_path=paths["source"],
            expected_source_sha256=sha256_file(paths["source"]),
            train_validation_path=new_train_validation,
            test_path=new_test,
            lock_path=new_lock,
        )
    assert not new_train_validation.exists()
    assert not new_test.exists()
    assert not new_lock.exists()


@pytest.mark.parametrize("mode", [RunMode.SMOKE, RunMode.VALIDATION])
def test_non_final_modes_never_open_test_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: RunMode
) -> None:
    paths = _fixture_project(tmp_path)
    test_path = paths["test"].resolve()
    original_open = Path.open
    opened: list[Path] = []

    def tracked_open(path: Path, *args: object, **kwargs: object):
        resolved = path.resolve()
        opened.append(resolved)
        if resolved == test_path:
            raise AssertionError("test manifest was opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracked_open)
    result = load_run_manifests(
        mode=mode,
        project_root=tmp_path,
        split_lock_path=paths["lock"],
        train_validation_manifest_path=paths["train_validation"],
        require_image_files=True,
        verify_image_hashes=True,
    )

    assert result.test is None
    assert test_path not in opened


@pytest.mark.parametrize("mode", [RunMode.SMOKE, RunMode.VALIDATION])
def test_non_final_modes_reject_test_capabilities_before_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: RunMode
) -> None:
    paths = _fixture_project(tmp_path)
    opened: list[Path] = []
    original_open = Path.open

    def tracked_open(path: Path, *args: object, **kwargs: object):
        opened.append(path.resolve())
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracked_open)
    with pytest.raises(ValueError, match="cannot receive test access"):
        load_run_manifests(
            mode=mode,
            project_root=tmp_path,
            split_lock_path=paths["lock"],
            train_validation_manifest_path=paths["train_validation"],
            test_manifest_path=paths["test"],
        )
    assert opened == []


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"confirmation": None}, "confirmation"),
        ({"test_open_reason": "   "}, "reason"),
        ({"frozen_manifest_path": None}, "requires test, frozen manifest"),
        ({"frozen_manifest_sha256": None}, "requires test, frozen manifest"),
    ],
)
def test_final_eval_requires_all_authorizations(
    tmp_path: Path, overrides: dict[str, object], message: str
) -> None:
    paths = _fixture_project(tmp_path)
    frozen = _write_frozen_manifest(paths)
    arguments: dict[str, object] = {
        "mode": RunMode.FINAL_EVAL,
        "project_root": tmp_path,
        "split_lock_path": paths["lock"],
        "train_validation_manifest_path": paths["train_validation"],
        "test_manifest_path": paths["test"],
        "frozen_manifest_path": frozen,
        "frozen_manifest_sha256": sha256_file(frozen),
        "confirmation": FINAL_EVAL_CONFIRMATION,
        "test_open_reason": "frozen model final evaluation",
        "receipt_directory": tmp_path / "reports/test-access",
    }
    arguments.update(overrides)
    with pytest.raises(ValueError, match=message):
        load_run_manifests(**arguments)  # type: ignore[arg-type]
    assert not (tmp_path / "reports/test-access").exists()


def test_final_eval_writes_receipt_before_test_open_and_chains_receipts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _fixture_project(tmp_path)
    frozen = _write_frozen_manifest(paths)
    receipt_directory = tmp_path / "reports/test-access"
    test_path = paths["test"].resolve()
    original_open = Path.open

    def tracked_open(path: Path, *args: object, **kwargs: object):
        if path.resolve() == test_path:
            assert list(receipt_directory.glob("[0-9]*.json"))
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracked_open)
    base_time = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    common = {
        "mode": RunMode.FINAL_EVAL,
        "project_root": tmp_path,
        "split_lock_path": paths["lock"],
        "train_validation_manifest_path": paths["train_validation"],
        "test_manifest_path": paths["test"],
        "frozen_manifest_path": frozen,
        "frozen_manifest_sha256": sha256_file(frozen),
        "confirmation": FINAL_EVAL_CONFIRMATION,
        "test_open_reason": "frozen model final evaluation",
        "receipt_directory": receipt_directory,
        "require_image_files": True,
        "verify_image_hashes": True,
    }
    first = load_run_manifests(
        **common,
        now=lambda: base_time,
        receipt_id_factory=lambda: "receipt-one",
    )
    second = load_run_manifests(
        **common,
        now=lambda: base_time + timedelta(seconds=1),
        receipt_id_factory=lambda: "receipt-two",
    )

    assert first.test is not None
    assert second.test is not None
    chain = validate_receipt_chain(receipt_directory)
    assert len(chain) == 2
    second_receipt = json.loads(chain[1].read_text(encoding="utf-8"))
    assert second_receipt["previous_receipt_sha256"] == sha256_file(chain[0])
    assert second_receipt["reason"] == "frozen model final evaluation"


def test_final_eval_rejects_mutated_checkpoint_before_test_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = _fixture_project(tmp_path)
    frozen = _write_frozen_manifest(paths)
    checkpoint = tmp_path / "data/experiments/checkpoint.bin"
    checkpoint.write_bytes(b"mutated")
    test_path = paths["test"].resolve()
    original_open = Path.open

    def tracked_open(path: Path, *args: object, **kwargs: object):
        if path.resolve() == test_path:
            raise AssertionError("test manifest was opened")
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", tracked_open)
    receipt_directory = tmp_path / "reports/test-access"
    with pytest.raises(ValueError, match="checkpoint"):
        load_run_manifests(
            mode=RunMode.FINAL_EVAL,
            project_root=tmp_path,
            split_lock_path=paths["lock"],
            train_validation_manifest_path=paths["train_validation"],
            test_manifest_path=paths["test"],
            frozen_manifest_path=frozen,
            frozen_manifest_sha256=sha256_file(frozen),
            confirmation=FINAL_EVAL_CONFIRMATION,
            test_open_reason="frozen model final evaluation",
            receipt_directory=receipt_directory,
        )
    assert not receipt_directory.exists()


def test_receipt_chain_detects_tampering(tmp_path: Path) -> None:
    paths = _fixture_project(tmp_path)
    frozen = _write_frozen_manifest(paths)
    receipt_directory = tmp_path / "reports/test-access"
    load_run_manifests(
        mode=RunMode.FINAL_EVAL,
        project_root=tmp_path,
        split_lock_path=paths["lock"],
        train_validation_manifest_path=paths["train_validation"],
        test_manifest_path=paths["test"],
        frozen_manifest_path=frozen,
        frozen_manifest_sha256=sha256_file(frozen),
        confirmation=FINAL_EVAL_CONFIRMATION,
        test_open_reason="frozen model final evaluation",
        receipt_directory=receipt_directory,
        now=lambda: datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
        receipt_id_factory=lambda: "receipt-one",
    )
    receipt_path = validate_receipt_chain(receipt_directory)[0]
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["reason"] = "tampered reason"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    with pytest.raises(ValueError, match="payload was modified"):
        validate_receipt_chain(receipt_directory)


@pytest.mark.parametrize("unsafe_path", ["../escape.png", "/absolute/image.png"])
def test_manifest_generation_rejects_paths_outside_project(
    tmp_path: Path, unsafe_path: str
) -> None:
    paths = _fixture_project(tmp_path)
    with paths["source"].open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    rows[0]["path"] = unsafe_path
    _write_csv(paths["source"], rows)

    with pytest.raises(ValueError, match="project root"):
        build_separated_manifests(
            project_root=tmp_path,
            source_path=paths["source"],
            expected_source_sha256=sha256_file(paths["source"]),
            train_validation_path=paths["train_validation"],
            test_path=paths["test"],
            lock_path=paths["lock"],
        )


def test_protocol_imports_without_torch(monkeypatch: pytest.MonkeyPatch) -> None:
    original_import = builtins.__import__

    def reject_torch_import(
        name: str,
        globals: object = None,
        locals: object = None,
        fromlist: tuple[str, ...] = (),
        level: int = 0,
    ):
        if name == "torch" or name.startswith("torch."):
            raise AssertionError("the protocol imported torch")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", reject_torch_import)
    for module_name in tuple(sys.modules):
        if module_name == "training.ooc_cnn" or module_name.startswith("training.ooc_cnn."):
            monkeypatch.delitem(sys.modules, module_name, raising=False)
    importlib.import_module("training.ooc_cnn")
