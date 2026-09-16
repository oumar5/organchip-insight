from pathlib import Path
from types import SimpleNamespace

import pytest

from training.ooc_cnn.configuration import ExperimentConfig
from training.ooc_cnn.engine import _resume_run_directory, _validate_resume_payload
from training.ooc_cnn.manifests import sha256_file
from training.ooc_cnn.protocol import RunMode
from training.ooc_cnn.weights import InitialWeights


def _config(tmp_path: Path) -> ExperimentConfig:
    config_path = tmp_path / "config.json"
    config_path.write_text("{}\n", encoding="utf-8")
    return ExperimentConfig(
        path=config_path,
        sha256=sha256_file(config_path),
        raw={},
        experiment_id="resume-fixture",
        split_lock_path=tmp_path / "lock.json",
        split_lock_sha256="0" * 64,
        train_validation_manifest_path=tmp_path / "train-validation.csv",
        train_validation_manifest_sha256="1" * 64,
        runs_directory=tmp_path / "runs",
        generated_reports_directory=tmp_path / "reports",
        test_receipts_directory=tmp_path / "receipts",
    )


def _weights(tmp_path: Path) -> InitialWeights:
    return InitialWeights(
        path=tmp_path / "weights.pt",
        sha256="2" * 64,
        metadata_path=tmp_path / "weights.json",
        metadata_sha256="3" * 64,
        architecture="mobilenet_v3_small",
        weight_enum="MobileNet_V3_Small_Weights.IMAGENET1K_V1",
        source_url="https://example.invalid/weights.pt",
        license="fixture",
    )


def test_resume_payload_is_bound_to_run_inputs(tmp_path: Path) -> None:
    config = _config(tmp_path)
    weights = _weights(tmp_path)
    best_checkpoint = tmp_path / "best-checkpoint.pt"
    best_checkpoint.write_bytes(b"best")
    source_files = [{"path": "engine.py", "sha256": "4" * 64, "size_bytes": 4}]
    runtime_identity = {"python": "3.12.13", "resolved_device": "cuda"}
    manifests = SimpleNamespace(
        train_validation=SimpleNamespace(sha256="5" * 64)
    )
    payload = {
        "schema_version": 2,
        "checkpoint_kind": "training-resume",
        "experiment_id": config.experiment_id,
        "architecture": "mobilenet_v3_small",
        "mode": "validation",
        "run_id": "validation-run",
        "config_sha256": config.sha256,
        "train_validation_manifest_sha256": manifests.train_validation.sha256,
        "initial_weights_sha256": weights.sha256,
        "source_files": source_files,
        "runtime_identity": runtime_identity,
        "completed_epoch": 2,
        "history": [{"epoch": 1}, {"epoch": 2}],
        "best_checkpoint_sha256": sha256_file(best_checkpoint),
        "model_state_dict": {},
        "optimizer_state_dict": {},
        "scheduler_state_dict": {},
        "scaler_state_dict": {},
        "best_key": (0.5, 0.5, -0.7),
        "best_epoch": 1,
        "epochs_without_improvement": 1,
        "rng_state": {},
        "train_generator_state": "fixture",
        "validation_generator_state": "fixture",
    }

    _validate_resume_payload(
        payload,
        config=config,
        manifests=manifests,
        run_id="validation-run",
        initial_weights=weights,
        source_files=source_files,
        runtime_identity=runtime_identity,
        epochs=20,
        best_checkpoint_path=best_checkpoint,
    )

    payload["config_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="config_sha256"):
        _validate_resume_payload(
            payload,
            config=config,
            manifests=manifests,
            run_id="validation-run",
            initial_weights=weights,
            source_files=source_files,
            runtime_identity=runtime_identity,
            epochs=20,
            best_checkpoint_path=best_checkpoint,
        )


def test_resume_requires_the_original_incomplete_run_directory(tmp_path: Path) -> None:
    config = _config(tmp_path)
    run_directory = config.runs_directory / "validation-run"
    run_directory.mkdir(parents=True)
    checkpoint = run_directory / "last-checkpoint.pt"
    checkpoint.write_bytes(b"resume")

    assert (
        _resume_run_directory(
            config,
            RunMode.VALIDATION,
            "validation-run",
            checkpoint,
        )
        == run_directory
    )

    other = tmp_path / "other.pt"
    other.write_bytes(b"other")
    with pytest.raises(ValueError, match="last checkpoint"):
        _resume_run_directory(
            config,
            RunMode.VALIDATION,
            "validation-run",
            other,
        )

    (run_directory / "validation-report.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Completed CNN runs"):
        _resume_run_directory(
            config,
            RunMode.VALIDATION,
            "validation-run",
            checkpoint,
        )
