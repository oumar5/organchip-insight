import json
from pathlib import Path

import pytest

from training.ooc_cnn.configuration import ExperimentConfig, load_experiment_config
from training.ooc_cnn.export import _load_selection_report
from training.ooc_cnn.freeze import create_frozen_manifest
from training.ooc_cnn.manifests import sha256_file
from training.ooc_cnn.provenance import artifact_record, source_hashes
from training.ooc_cnn.runtime_contract import validate_required_hashes
from training.ooc_cnn.weights import load_initial_weights

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


@pytest.mark.parametrize(
    ("file_name", "experiment_id"),
    (
        (
            "ooc-cnn-mobilenet-v3-small-v1.json",
            "ooc-cnn-mobilenet-v3-small-v1",
        ),
        (
            "ooc-cnn-mobilenet-v3-small-campaign-v2.json",
            "ooc-cnn-mobilenet-v3-small-campaign-v2",
        ),
    ),
)
def test_repository_cnn_config_is_self_consistent(
    file_name: str, experiment_id: str
) -> None:
    config_path = PROJECT_ROOT / "backend/training/configs" / file_name

    config = load_experiment_config(config_path, project_root=PROJECT_ROOT)

    assert config.experiment_id == experiment_id
    assert config.train_validation_manifest_sha256 == sha256_file(
        config.train_validation_manifest_path
    )
    assert config.split_lock_sha256 == sha256_file(config.split_lock_path)


def test_runtime_contract_requires_only_hashes_consumed_by_each_mode() -> None:
    contract_path = (
        PROJECT_ROOT / "backend/experiments/ooc-cnn/kaggle-runtime-contract.json"
    )
    contract_sha256 = sha256_file(contract_path)
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    common_names = contract["required_hashes"]["all_modes"]
    common = {name: "0" * 64 for name in common_names}

    smoke = validate_required_hashes(
        contract_path=contract_path,
        expected_sha256=contract_sha256,
        mode="smoke",
        provided_hashes=common,
    )
    validation = validate_required_hashes(
        contract_path=contract_path,
        expected_sha256=contract_sha256,
        mode="validation",
        provided_hashes={**common, "initial_weights_sha256": "1" * 64},
    )
    final = validate_required_hashes(
        contract_path=contract_path,
        expected_sha256=contract_sha256,
        mode="final-eval",
        provided_hashes={
            **common,
            "frozen_manifest_sha256": "2" * 64,
            "checkpoint_sha256": "3" * 64,
            "test_manifest_sha256": "4" * 64,
        },
    )

    assert set(smoke) == set(common_names)
    assert set(validation) == {*common_names, "initial_weights_sha256"}
    assert set(final) == {
        *common_names,
        "frozen_manifest_sha256",
        "checkpoint_sha256",
        "test_manifest_sha256",
    }
    assert contract["modes"]["final-eval"]["pretrained_weights_required"] is False
    assert contract["local_inputs"]["initial_weights"]["required_for_modes"] == [
        "validation"
    ]
    assert not {
        "initial_weights_sha256",
        "preprocessing_sha256",
        "labels_sha256",
    } & set(final)

    with pytest.raises(RuntimeError, match="checkpoint_sha256"):
        validate_required_hashes(
            contract_path=contract_path,
            expected_sha256=contract_sha256,
            mode="final-eval",
            provided_hashes={
                **common,
                "frozen_manifest_sha256": "2" * 64,
                "test_manifest_sha256": "4" * 64,
            },
        )


def test_initial_weights_require_the_pinned_torchvision_provenance(
    tmp_path: Path,
) -> None:
    weights = tmp_path / "mobilenet_v3_small-imagenet1k-v1.pth"
    weights.write_bytes(b"fixture weights")
    digest = sha256_file(weights)
    metadata = tmp_path / "weights.json"
    value = {
        "schema_version": 1,
        "file_name": weights.name,
        "file_sha256": digest,
        "architecture": "mobilenet_v3_small",
        "weight_enum": "MobileNet_V3_Small_Weights.IMAGENET1K_V1",
        "source_url": (
            "https://download.pytorch.org/models/"
            "mobilenet_v3_small-047dcff4.pth"
        ),
        "license": "BSD-3-Clause (torchvision); ImageNet terms apply",
    }
    _write_json(metadata, value)

    loaded = load_initial_weights(
        weights_path=weights,
        expected_sha256=digest,
        metadata_path=metadata,
    )
    assert loaded.weight_enum == value["weight_enum"]

    value["weight_enum"] = "untrusted-two-class-checkpoint"
    _write_json(metadata, value)
    with pytest.raises(ValueError, match="pinned torchvision weight enum"):
        load_initial_weights(
            weights_path=weights,
            expected_sha256=digest,
            metadata_path=metadata,
        )


def test_selection_report_cryptographically_binds_export_inputs(tmp_path: Path) -> None:
    config_path = tmp_path / "config.json"
    checkpoint_path = tmp_path / "run/best-checkpoint.pt"
    config_path.write_text("{}\n", encoding="utf-8")
    checkpoint_path.parent.mkdir(parents=True)
    checkpoint_path.write_bytes(b"checkpoint")
    config = ExperimentConfig(
        path=config_path,
        sha256=sha256_file(config_path),
        raw={},
        experiment_id="fixture-cnn",
        split_lock_path=tmp_path / "lock.json",
        split_lock_sha256="0" * 64,
        train_validation_manifest_path=tmp_path / "train-validation.csv",
        train_validation_manifest_sha256="1" * 64,
        runs_directory=tmp_path / "runs",
        generated_reports_directory=tmp_path / "reports",
        test_receipts_directory=tmp_path / "receipts",
    )
    report_path = tmp_path / "run/validation-report.json"
    report = {
        "schema_version": 1,
        "experiment_id": config.experiment_id,
        "mode": "smoke",
        "benchmark_eligible": False,
        "config": artifact_record(tmp_path, config_path),
        "split": {"test_manifest_opened": False},
        "selection": {"threshold": 0.42, "threshold_selected_on": "validation"},
        "artifacts": {"checkpoint": artifact_record(tmp_path, checkpoint_path)},
    }
    _write_json(report_path, report)

    loaded, threshold = _load_selection_report(
        project_root=tmp_path,
        config=config,
        checkpoint_path=checkpoint_path,
        checkpoint_sha256=sha256_file(checkpoint_path),
        report_path=report_path,
        report_sha256=sha256_file(report_path),
    )
    assert loaded["mode"] == "smoke"
    assert threshold == 0.42

    checkpoint_path.write_bytes(b"different checkpoint")
    with pytest.raises(ValueError, match="checkpoint provenance"):
        _load_selection_report(
            project_root=tmp_path,
            config=config,
            checkpoint_path=checkpoint_path,
            checkpoint_sha256=sha256_file(checkpoint_path),
            report_path=report_path,
            report_sha256=sha256_file(report_path),
        )


def test_freeze_rejects_code_changed_after_validation(tmp_path: Path) -> None:
    source_manifest = tmp_path / "data/splits/source.csv"
    train_validation = tmp_path / "data/splits/train-validation.csv"
    test_manifest = tmp_path / "data/splits/test.csv"
    for path, content in (
        (source_manifest, "source\n"),
        (train_validation, "train-validation\n"),
        (test_manifest, "test\n"),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    lock_path = tmp_path / "data/splits/lock.json"
    lock = {
        "schema_version": 1,
        "split_id": "fixture",
        "source": {
            "path": "data/splits/source.csv",
            "sha256": sha256_file(source_manifest),
            "rows": 3,
        },
        "manifests": {
            "train_validation": {
                "path": "data/splits/train-validation.csv",
                "sha256": sha256_file(train_validation),
                "rows": 2,
                "split_counts": {"train": 1, "validation": 1},
                "groups": {"train": ["train-group"], "validation": ["val-group"]},
            },
            "test": {
                "path": "data/splits/test.csv",
                "sha256": sha256_file(test_manifest),
                "rows": 1,
                "split_counts": {"test": 1},
                "groups": {"test": ["test-group"]},
            },
        },
        "group_overlaps": {
            "train_validation": [],
            "train_test": [],
            "validation_test": [],
        },
    }
    _write_json(lock_path, lock)
    config_path = tmp_path / "config.json"
    _write_json(config_path, {"experiment_id": "fixture-cnn"})
    checkpoint_path = tmp_path / "run/best-checkpoint.pt"
    checkpoint_path.parent.mkdir(parents=True)
    checkpoint_path.write_bytes(b"checkpoint")
    source_path = tmp_path / "backend/training/ooc_cnn/engine.py"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("# validation source\n", encoding="utf-8")
    report_path = tmp_path / "run/validation-report.json"
    report = {
        "schema_version": 1,
        "mode": "validation",
        "benchmark_eligible": True,
        "experiment_id": "fixture-cnn",
        "config": artifact_record(tmp_path, config_path),
        "split": {
            "lock_sha256": sha256_file(lock_path),
            "train_validation_manifest_sha256": sha256_file(train_validation),
            "test_manifest_opened": False,
        },
        "training": {"device": "cuda"},
        "initialization": {"external_weights": True},
        "selection": {
            "checkpoint_metric": "validation macro_f1 at threshold 0.5",
            "best_epoch": 1,
            "threshold": 0.5,
            "threshold_selected_on": "validation",
        },
        "source_files": source_hashes(tmp_path, [source_path]),
        "artifacts": {"checkpoint": artifact_record(tmp_path, checkpoint_path)},
    }
    _write_json(report_path, report)
    source_path.write_text("# changed after validation\n", encoding="utf-8")

    with pytest.raises(ValueError, match="source hashes"):
        create_frozen_manifest(
            project_root=tmp_path,
            config_path=config_path,
            validation_report_path=report_path,
            checkpoint_path=checkpoint_path,
            split_lock_path=lock_path,
            split_lock_sha256=sha256_file(lock_path),
            output_path=tmp_path / "run/frozen.json",
            source_paths=[source_path],
        )
