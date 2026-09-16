"""Command-line entry point shared by local and Kaggle OoC CNN runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from training.ooc_cnn.archive import create_artifact_archive
from training.ooc_cnn.configuration import ExperimentConfig, load_experiment_config
from training.ooc_cnn.engine import (
    assert_run_destination_available,
    run_final_evaluation,
    run_training,
)
from training.ooc_cnn.export import export_checkpoint
from training.ooc_cnn.freeze import create_frozen_manifest
from training.ooc_cnn.manifests import resolve_project_path, sha256_file
from training.ooc_cnn.model import build_mobilenet_v3_small
from training.ooc_cnn.protocol import (
    FINAL_EVAL_CONFIRMATION,
    RunMode,
    load_frozen_manifest,
    load_run_manifests,
)
from training.ooc_cnn.runtime_contract import validate_runtime_contract
from training.ooc_cnn.weights import InitialWeights, load_initial_weights

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = (
    PROJECT_ROOT / "backend/training/configs/ooc-cnn-mobilenet-v3-small-v1.json"
)


def _add_common_config(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    train = subparsers.add_parser("train", help="Run smoke or validation training")
    _add_common_config(train)
    train.add_argument("--mode", choices=("smoke", "validation"), required=True)
    train.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    train.add_argument("--weights", type=Path)
    train.add_argument("--weights-sha256")
    train.add_argument("--weights-metadata", type=Path)
    train.add_argument("--run-id")
    train.add_argument("--resume-from", type=Path)
    train.add_argument("--image-root", type=Path, default=PROJECT_ROOT)
    train.add_argument("--skip-image-hash-verification", action="store_true")

    freeze = subparsers.add_parser("freeze", help="Freeze a validation-selected run")
    _add_common_config(freeze)
    freeze.add_argument("--validation-report", type=Path, required=True)
    freeze.add_argument("--checkpoint", type=Path, required=True)
    freeze.add_argument("--output", type=Path, required=True)

    final = subparsers.add_parser(
        "final-eval",
        help="Open the frozen test after persisting a workspace-scoped receipt",
    )
    _add_common_config(final)
    final.add_argument("--device", choices=("auto", "cuda"), default="auto")
    final.add_argument("--test-manifest", type=Path, required=True)
    final.add_argument("--test-manifest-root", type=Path, default=PROJECT_ROOT)
    final.add_argument("--frozen-manifest", type=Path, required=True)
    final.add_argument("--frozen-manifest-sha256", required=True)
    final.add_argument("--confirm-test-open", required=True)
    final.add_argument("--reason", required=True)
    final.add_argument("--run-id", required=True)
    final.add_argument("--image-root", type=Path, default=PROJECT_ROOT)

    export = subparsers.add_parser("export", help="Export and verify an ONNX model")
    _add_common_config(export)
    export.add_argument("--checkpoint", type=Path, required=True)
    export.add_argument("--checkpoint-sha256", required=True)
    export.add_argument("--selection-report", type=Path, required=True)
    export.add_argument("--selection-report-sha256", required=True)
    export.add_argument("--output-directory", type=Path, required=True)

    archive = subparsers.add_parser(
        "archive", help="Create a deterministic ZIP of one completed run"
    )
    archive.add_argument("--run-directory", type=Path, required=True)
    archive.add_argument("--output", type=Path, required=True)
    archive.add_argument("--source-bundle-sha256", required=True)
    archive.add_argument("--source-commit", required=True)
    archive.add_argument("--archive-root")
    return parser


def _contract(config: ExperimentConfig, mode: RunMode, device: str) -> tuple[str, dict[str, Any]]:
    provenance = config.raw["provenance"]
    contract_path = resolve_project_path(
        PROJECT_ROOT,
        provenance["runtime_contract_path"],
        field="runtime contract",
    )
    return validate_runtime_contract(
        contract_path=contract_path,
        expected_sha256=provenance["runtime_contract_sha256"],
        mode=mode,
        requested_device=device,
    )


def _resolve_image_root(path: Path) -> Path:
    return (path if path.is_absolute() else PROJECT_ROOT / path).resolve()


def _load_training_manifests(
    config: ExperimentConfig,
    mode: RunMode,
    image_root: Path,
):
    manifests = load_run_manifests(
        mode=mode,
        project_root=PROJECT_ROOT,
        image_root=image_root,
        split_lock_path=config.split_lock_path,
        split_lock_sha256=config.split_lock_sha256,
        train_validation_manifest_path=config.train_validation_manifest_path,
    )
    if manifests.train_validation.sha256 != config.train_validation_manifest_sha256:
        raise ValueError("Active train/validation manifest does not match the CNN config")
    return manifests


def _weights_for_training(
    arguments: argparse.Namespace, mode: RunMode
) -> InitialWeights | None:
    values = (arguments.weights, arguments.weights_sha256, arguments.weights_metadata)
    if mode is RunMode.SMOKE:
        if any(value is not None for value in values):
            raise ValueError("Smoke mode forbids external initialization weights")
        return None
    if any(value is None for value in values):
        raise ValueError(
            "Validation requires --weights, --weights-sha256, and --weights-metadata"
        )
    return load_initial_weights(
        weights_path=arguments.weights,
        expected_sha256=arguments.weights_sha256,
        metadata_path=arguments.weights_metadata,
    )


def _run_train(arguments: argparse.Namespace, config: ExperimentConfig) -> dict[str, Any]:
    mode = RunMode(arguments.mode)
    if arguments.resume_from is not None and mode is not RunMode.VALIDATION:
        raise ValueError("--resume-from is restricted to validation mode")
    if mode is RunMode.VALIDATION and arguments.skip_image_hash_verification:
        raise ValueError("Validation cannot skip image hash verification")
    resolved_device, runtime = _contract(config, mode, arguments.device)
    image_root = _resolve_image_root(arguments.image_root)
    manifests = _load_training_manifests(config, mode, image_root)
    weights = _weights_for_training(arguments, mode)
    report = run_training(
        project_root=PROJECT_ROOT,
        image_root=image_root,
        config=config,
        manifests=manifests,
        mode=mode,
        device_name=resolved_device,
        runtime_snapshot=runtime,
        initial_weights=weights,
        run_id=arguments.run_id,
        verify_image_hashes=not arguments.skip_image_hash_verification,
        resume_checkpoint=(
            arguments.resume_from.resolve() if arguments.resume_from is not None else None
        ),
    )
    return {
        "mode": report["mode"],
        "run_id": report["run_id"],
        "benchmark_eligible": report["benchmark_eligible"],
        "selection": report["selection"],
        "report_paths": report["report_paths"],
    }


def _run_freeze(arguments: argparse.Namespace, config: ExperimentConfig) -> dict[str, Any]:
    source_paths = sorted((PROJECT_ROOT / "backend/training/ooc_cnn").glob("*.py"))
    create_frozen_manifest(
        project_root=PROJECT_ROOT,
        config_path=config.path,
        validation_report_path=arguments.validation_report.resolve(),
        checkpoint_path=arguments.checkpoint.resolve(),
        split_lock_path=config.split_lock_path,
        split_lock_sha256=config.split_lock_sha256,
        output_path=arguments.output.resolve(),
        source_paths=source_paths,
    )
    return {
        "frozen_manifest": str(arguments.output.resolve()),
        "sha256": sha256_file(arguments.output.resolve()),
        "test_manifest_opened": False,
    }


def _run_final(arguments: argparse.Namespace, config: ExperimentConfig) -> dict[str, Any]:
    resolved_device, runtime = _contract(config, RunMode.FINAL_EVAL, arguments.device)
    image_root = _resolve_image_root(arguments.image_root)
    assert_run_destination_available(config, RunMode.FINAL_EVAL, arguments.run_id)
    active_source_paths = tuple(
        sorted((PROJECT_ROOT / "backend/training/ooc_cnn").glob("*.py"))
    )
    preflight_frozen = load_frozen_manifest(
        arguments.frozen_manifest.resolve(),
        project_root=PROJECT_ROOT,
        expected_sha256=arguments.frozen_manifest_sha256,
        deferred_artifacts=frozenset({"test_manifest"}),
        expected_source_paths=active_source_paths,
    )
    checkpoint = preflight_frozen.artifacts["checkpoint"]
    build_mobilenet_v3_small(
        weights=checkpoint.path,
        expected_sha256=checkpoint.sha256,
        weights_role="checkpoint",
    )
    manifests = load_run_manifests(
        mode=RunMode.FINAL_EVAL,
        project_root=PROJECT_ROOT,
        image_root=image_root,
        split_lock_path=config.split_lock_path,
        split_lock_sha256=config.split_lock_sha256,
        train_validation_manifest_path=config.train_validation_manifest_path,
        test_manifest_path=arguments.test_manifest.resolve(),
        test_manifest_root=_resolve_image_root(arguments.test_manifest_root),
        frozen_manifest_path=arguments.frozen_manifest.resolve(),
        frozen_manifest_sha256=arguments.frozen_manifest_sha256,
        confirmation=arguments.confirm_test_open,
        test_open_reason=arguments.reason,
        receipt_directory=config.test_receipts_directory,
        active_config_path=config.path,
        active_config_sha256=config.sha256,
        active_source_paths=active_source_paths,
        require_image_files=True,
        verify_image_hashes=True,
    )
    if manifests.frozen_manifest is None:
        raise AssertionError("Final evaluation did not load a frozen manifest")
    report = run_final_evaluation(
        project_root=PROJECT_ROOT,
        image_root=image_root,
        config=config,
        manifests=manifests,
        frozen=manifests.frozen_manifest,
        device_name=resolved_device,
        runtime_snapshot=runtime,
        run_id=arguments.run_id,
        verify_image_hashes=True,
    )
    return {
        "mode": report["mode"],
        "run_id": report["run_id"],
        "test": report["test"],
        "report_paths": report["report_paths"],
    }


def _run_export(arguments: argparse.Namespace, config: ExperimentConfig) -> dict[str, Any]:
    _device, runtime = _contract(config, RunMode.SMOKE, "cpu")
    contract_validation_mode = runtime.pop("mode")
    runtime = {
        **runtime,
        "contract_validation_mode": contract_validation_mode,
        "operation": "onnx-export",
        "execution_device": "cpu",
    }
    return export_checkpoint(
        project_root=PROJECT_ROOT,
        config=config,
        checkpoint_path=arguments.checkpoint.resolve(),
        checkpoint_sha256=arguments.checkpoint_sha256,
        selection_report_path=arguments.selection_report.resolve(),
        selection_report_sha256=arguments.selection_report_sha256,
        output_directory=arguments.output_directory.resolve(),
        runtime_snapshot=runtime,
    )


def main() -> None:
    arguments = _parser().parse_args()
    if arguments.command == "archive":
        output = create_artifact_archive(
            run_directory=arguments.run_directory,
            output_path=arguments.output,
            source_bundle_sha256=arguments.source_bundle_sha256,
            source_commit=arguments.source_commit,
            archive_root=arguments.archive_root,
        )
        print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
        return
    config_path = (
        arguments.config
        if arguments.config.is_absolute()
        else PROJECT_ROOT / arguments.config
    )
    config = load_experiment_config(config_path.resolve(), project_root=PROJECT_ROOT)
    if arguments.command == "train":
        output = _run_train(arguments, config)
    elif arguments.command == "freeze":
        output = _run_freeze(arguments, config)
    elif arguments.command == "final-eval":
        if arguments.confirm_test_open != FINAL_EVAL_CONFIRMATION:
            raise ValueError(
                f"Final evaluation requires --confirm-test-open {FINAL_EVAL_CONFIRMATION}"
            )
        output = _run_final(arguments, config)
    elif arguments.command == "export":
        output = _run_export(arguments, config)
    else:
        raise AssertionError(f"Unsupported command: {arguments.command}")
    print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
