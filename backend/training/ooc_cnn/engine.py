"""Shared PyTorch training and final-evaluation engine for OoC image quality."""

from __future__ import annotations

import csv
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from training.ooc_cnn.configuration import ExperimentConfig
from training.ooc_cnn.dataset import ManifestImageDataset, select_smoke_records
from training.ooc_cnn.manifests import ManifestRecord, relative_project_path, sha256_file
from training.ooc_cnn.metrics import (
    binary_metrics,
    bootstrap_metrics_by_group,
    metrics_by_slice,
    select_threshold,
)
from training.ooc_cnn.model import build_mobilenet_v3_small
from training.ooc_cnn.preprocessing import build_image_transform
from training.ooc_cnn.protocol import FrozenManifest, RunManifests, RunMode
from training.ooc_cnn.provenance import (
    artifact_record,
    environment_snapshot,
    git_state,
    source_hashes,
    utc_now,
    write_json_atomic,
)
from training.ooc_cnn.weights import InitialWeights

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def _import_torch() -> tuple[Any, Any, Any]:
    try:
        import torch
        from torch import nn
        from torch.utils.data import DataLoader
    except (ImportError, RuntimeError) as error:
        raise RuntimeError("The isolated CNN runtime with PyTorch is required") from error
    return torch, nn, DataLoader


def _seed_everything(torch: Any, seed: int) -> None:
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.benchmark = False
        torch.backends.cudnn.deterministic = True


def _seed_worker(worker_id: int) -> None:
    del worker_id
    torch, _nn, _loader = _import_torch()
    worker_seed = int(torch.initial_seed() % (2**32))
    random.seed(worker_seed)
    np.random.seed(worker_seed)


def _run_id(mode: RunMode, requested: str | None) -> str:
    if requested is None:
        timestamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        return f"{mode.value}-{timestamp}"
    if not RUN_ID_PATTERN.fullmatch(requested):
        raise ValueError("run_id may contain only letters, numbers, dot, dash, and underscore")
    return requested


def _prepare_run_directory(config: ExperimentConfig, mode: RunMode, run_id: str | None) -> Path:
    path = assert_run_destination_available(config, mode, run_id)
    path.mkdir(parents=True)
    return path


def assert_run_destination_available(
    config: ExperimentConfig,
    mode: RunMode,
    run_id: str | None,
) -> Path:
    """Fail before data access when a requested run destination is already occupied."""
    path = config.runs_directory / _run_id(mode, run_id)
    if path.exists():
        raise ValueError(f"CNN run directory already exists: {path}")
    return path


def _visible_records(
    manifests: RunManifests,
    config: ExperimentConfig,
    mode: RunMode,
) -> tuple[list[ManifestRecord], list[ManifestRecord]]:
    records = manifests.train_validation.records
    if mode is RunMode.SMOKE:
        smoke = config.raw["smoke"]
        selected = select_smoke_records(
            records,
            seed=int(config.raw["training"]["seed"]),
            max_records_by_split={
                "train": int(smoke["max_train_images"]),
                "validation": int(smoke["max_validation_images"]),
            },
        )
        train = [record for record in selected if record.grouped_split == "train"]
        validation = [
            record for record in selected if record.grouped_split == "validation"
        ]
    elif mode is RunMode.VALIDATION:
        train = [record for record in records if record.grouped_split == "train"]
        validation = [record for record in records if record.grouped_split == "validation"]
    else:
        raise ValueError("Training is restricted to smoke and validation modes")
    if not train or not validation:
        raise ValueError("Both train and validation records are required")
    if {record.target_index for record in train} != {0, 1}:
        raise ValueError("Training records must contain both target classes")
    if {record.target_index for record in validation} != {0, 1}:
        raise ValueError("Validation records must contain both target classes")
    return train, validation


def _image_slices(records: list[ManifestRecord], image_root: Path) -> dict[str, list[str]]:
    modes: list[str] = []
    resolutions: list[str] = []
    for record in records:
        image_path = image_root / record.path
        with Image.open(image_path) as image:
            modes.append(image.mode)
            resolutions.append(f"{image.width}x{image.height}")
    return {
        "cell_type": [record.cell_type for record in records],
        "day_bucket": [record.day_bucket for record in records],
        "image_mode": modes,
        "resolution": resolutions,
    }


def _make_loader(
    records: list[ManifestRecord],
    *,
    image_root: Path,
    training: bool,
    batch_size: int,
    workers: int,
    seed: int,
    verify_hashes: bool,
) -> Any:
    torch, _nn, DataLoader = _import_torch()
    dataset = ManifestImageDataset(
        records,
        image_root,
        transform=build_image_transform(training=training),
        verify_hashes=verify_hashes,
    )
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=training,
        num_workers=workers,
        pin_memory=torch.cuda.is_available(),
        worker_init_fn=_seed_worker if workers else None,
        generator=generator,
        # Restart workers at every epoch so that the saved generator state is enough
        # to reproduce the next epoch after a process interruption.
        persistent_workers=False,
    )


def _class_weights(records: list[ManifestRecord]) -> np.ndarray:
    counts = np.bincount([record.target_index for record in records], minlength=2)
    if np.any(counts == 0):
        raise ValueError("Class weighting requires both training classes")
    return len(records) / (2.0 * counts.astype(np.float64))


def _evaluate_loader(
    model: Any,
    loader: Any,
    *,
    device: Any,
    criterion: Any,
) -> tuple[float, np.ndarray, np.ndarray, float]:
    torch, _nn, _loader = _import_torch()
    model.eval()
    losses: list[float] = []
    labels: list[int] = []
    probabilities: list[float] = []
    started = time.perf_counter()
    with torch.inference_mode():
        for images, targets in loader:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            logits = model(images)
            loss = criterion(logits, targets)
            batch_probabilities = torch.softmax(logits, dim=1)[:, 1]
            losses.append(float(loss.detach().cpu()))
            labels.extend(int(value) for value in targets.detach().cpu().tolist())
            probabilities.extend(
                float(value) for value in batch_probabilities.detach().cpu().tolist()
            )
    elapsed = time.perf_counter() - started
    return (
        float(np.mean(losses)),
        np.asarray(labels, dtype=np.int64),
        np.asarray(probabilities, dtype=np.float64),
        elapsed,
    )


def _save_checkpoint(path: Path, payload: dict[str, Any], torch: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    torch.save(payload, temporary)
    temporary.replace(path)


def _capture_rng_state(torch: Any) -> dict[str, Any]:
    numpy_state = np.random.get_state()
    return {
        "python": random.getstate(),
        "numpy": {
            "bit_generator": numpy_state[0],
            "state": numpy_state[1].tolist(),
            "position": int(numpy_state[2]),
            "has_gauss": int(numpy_state[3]),
            "cached_gaussian": float(numpy_state[4]),
        },
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def _restore_rng_state(torch: Any, state: dict[str, Any]) -> None:
    numpy_state = state["numpy"]
    random.setstate(state["python"])
    np.random.set_state(
        (
            numpy_state["bit_generator"],
            np.asarray(numpy_state["state"], dtype=np.uint32),
            int(numpy_state["position"]),
            int(numpy_state["has_gauss"]),
            float(numpy_state["cached_gaussian"]),
        )
    )
    torch.set_rng_state(state["torch_cpu"])
    if torch.cuda.is_available():
        torch.cuda.set_rng_state_all(state["torch_cuda"])


def _resume_runtime_identity(snapshot: dict[str, Any]) -> dict[str, Any]:
    names = (
        "contract_sha256",
        "python",
        "packages",
        "torch_cuda_version",
        "cudnn_version",
        "gpu_count",
        "gpu_names",
        "resolved_device",
    )
    return {name: snapshot.get(name) for name in names}


def _resume_run_directory(
    config: ExperimentConfig,
    mode: RunMode,
    run_id: str | None,
    resume_checkpoint: Path,
) -> Path:
    if mode is not RunMode.VALIDATION:
        raise ValueError("Only validation training can be resumed")
    if run_id is None:
        raise ValueError("Resume requires the original explicit run_id")
    run_directory = config.runs_directory / _run_id(mode, run_id)
    expected = (run_directory / "last-checkpoint.pt").resolve()
    supplied = resume_checkpoint.resolve(strict=True)
    if supplied != expected:
        raise ValueError(f"Resume checkpoint must be the run last checkpoint: {expected}")
    if (run_directory / "validation-report.json").exists():
        raise ValueError("Completed CNN runs cannot be resumed")
    return run_directory


def _validate_resume_payload(
    payload: dict[str, Any],
    *,
    config: ExperimentConfig,
    manifests: RunManifests,
    run_id: str,
    initial_weights: InitialWeights,
    source_files: list[dict[str, Any]],
    runtime_identity: dict[str, Any],
    epochs: int,
    best_checkpoint_path: Path,
) -> None:
    expected = {
        "schema_version": 2,
        "checkpoint_kind": "training-resume",
        "experiment_id": config.experiment_id,
        "architecture": "mobilenet_v3_small",
        "mode": RunMode.VALIDATION.value,
        "run_id": run_id,
        "config_sha256": config.sha256,
        "train_validation_manifest_sha256": manifests.train_validation.sha256,
        "initial_weights_sha256": initial_weights.sha256,
        "source_files": source_files,
        "runtime_identity": runtime_identity,
    }
    mismatches = [name for name, value in expected.items() if payload.get(name) != value]
    if mismatches:
        raise ValueError(f"Resume checkpoint provenance mismatch: {', '.join(mismatches)}")
    completed_epoch = payload.get("completed_epoch")
    if (
        isinstance(completed_epoch, bool)
        or not isinstance(completed_epoch, int)
        or not 1 <= completed_epoch <= epochs
    ):
        raise ValueError("Resume checkpoint completed_epoch is invalid")
    history = payload.get("history")
    if not isinstance(history, list) or len(history) != completed_epoch:
        raise ValueError("Resume checkpoint history is incomplete")
    if [row.get("epoch") for row in history if isinstance(row, dict)] != list(
        range(1, completed_epoch + 1)
    ):
        raise ValueError("Resume checkpoint history epochs are invalid")
    required_state = (
        "model_state_dict",
        "optimizer_state_dict",
        "scheduler_state_dict",
        "scaler_state_dict",
        "best_key",
        "best_epoch",
        "epochs_without_improvement",
        "rng_state",
        "train_generator_state",
        "validation_generator_state",
    )
    missing_state = [name for name in required_state if name not in payload]
    if missing_state:
        raise ValueError(f"Resume checkpoint state is incomplete: {', '.join(missing_state)}")
    if not best_checkpoint_path.is_file():
        raise FileNotFoundError(best_checkpoint_path)
    if sha256_file(best_checkpoint_path) != payload.get("best_checkpoint_sha256"):
        raise ValueError("Resume checkpoint does not match the best checkpoint")


def _write_history(path: Path, history: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(history[0]))
        writer.writeheader()
        writer.writerows(history)


def _write_predictions(
    path: Path,
    records: list[ManifestRecord],
    probabilities: np.ndarray,
    threshold: float,
) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        fields = [
            "path",
            "image_id",
            "acquisition_prefix",
            "target_label",
            "target_index",
            "probability_good",
            "predicted_label",
            "correct",
            "cell_type",
            "day_bucket",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for record, probability in zip(records, probabilities, strict=True):
            prediction = int(probability >= threshold)
            writer.writerow(
                {
                    "path": record.path,
                    "image_id": record.image_id,
                    "acquisition_prefix": record.acquisition_prefix,
                    "target_label": record.target_label,
                    "target_index": record.target_index,
                    "probability_good": f"{probability:.10f}",
                    "predicted_label": "good" if prediction else "bad",
                    "correct": prediction == record.target_index,
                    "cell_type": record.cell_type,
                    "day_bucket": record.day_bucket,
                }
            )


def _plot_history(path: Path, history: list[dict[str, Any]]) -> None:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    epochs = [row["epoch"] for row in history]
    figure, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(epochs, [row["train_loss"] for row in history], label="train")
    axes[0].plot(epochs, [row["validation_loss"] for row in history], label="validation")
    axes[0].set_title("Loss")
    axes[0].set_xlabel("Epoch")
    axes[0].legend()
    axes[1].plot(epochs, [row["validation_macro_f1_at_0_5"] for row in history])
    axes[1].set_title("Validation macro-F1 · seuil 0,5")
    axes[1].set_xlabel("Epoch")
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _plot_confusion(path: Path, matrix: list[list[int]], title: str) -> None:
    import matplotlib

    matplotlib.use("Agg")
    from matplotlib import pyplot as plt

    values = np.asarray(matrix, dtype=np.int64)
    figure, axis = plt.subplots(figsize=(4.6, 4.2))
    image = axis.imshow(values, cmap="Greens")
    for row in range(2):
        for column in range(2):
            axis.text(column, row, str(values[row, column]), ha="center", va="center")
    axis.set_xticks([0, 1], ["bad", "good"])
    axis.set_yticks([0, 1], ["bad", "good"])
    axis.set_xlabel("Prédiction")
    axis.set_ylabel("Vérité terrain")
    axis.set_title(title)
    figure.colorbar(image, ax=axis, fraction=0.046)
    figure.tight_layout()
    figure.savefig(path, dpi=150)
    plt.close(figure)


def _source_paths(project_root: Path) -> list[Path]:
    package_root = project_root / "backend/training/ooc_cnn"
    return sorted(package_root.glob("*.py"))


def _display_path(project_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def run_training(
    *,
    project_root: Path,
    image_root: Path | None,
    config: ExperimentConfig,
    manifests: RunManifests,
    mode: RunMode,
    device_name: str,
    runtime_snapshot: dict[str, Any],
    initial_weights: InitialWeights | None,
    run_id: str | None = None,
    verify_image_hashes: bool = True,
    resume_checkpoint: Path | None = None,
) -> dict[str, Any]:
    if mode not in {RunMode.SMOKE, RunMode.VALIDATION}:
        raise ValueError("run_training supports only smoke and validation")
    if mode is RunMode.VALIDATION and initial_weights is None:
        raise ValueError("Validation requires explicit local pretrained weights")
    if mode is RunMode.VALIDATION and device_name != "cuda":
        raise ValueError("Benchmark-eligible validation requires CUDA")
    if mode is RunMode.VALIDATION and not verify_image_hashes:
        raise ValueError("Benchmark-eligible validation requires image hash verification")
    if mode is RunMode.SMOKE and initial_weights is not None:
        raise ValueError("Smoke mode must use initialization='none'")
    if resume_checkpoint is not None and mode is not RunMode.VALIDATION:
        raise ValueError("Only validation training can be resumed")

    root = project_root.resolve()
    resolved_image_root = (image_root or root).resolve()
    if not resolved_image_root.is_dir():
        raise ValueError("CNN image root is missing or not a directory")
    torch, nn, _loader = _import_torch()
    seed = int(config.raw["training"]["seed"])
    _seed_everything(torch, seed)
    device = torch.device(device_name)
    run_directory = (
        _resume_run_directory(config, mode, run_id, resume_checkpoint)
        if resume_checkpoint is not None
        else _prepare_run_directory(config, mode, run_id)
    )
    train_records, validation_records = _visible_records(manifests, config, mode)
    settings = config.raw["smoke"] if mode is RunMode.SMOKE else config.raw["training"]
    epochs = int(settings["epochs"])
    batch_size = int(settings["batch_size"])
    workers = int(settings["workers"])

    train_loader = _make_loader(
        train_records,
        image_root=resolved_image_root,
        training=True,
        batch_size=batch_size,
        workers=workers,
        seed=seed,
        verify_hashes=verify_image_hashes,
    )
    validation_loader = _make_loader(
        validation_records,
        image_root=resolved_image_root,
        training=False,
        batch_size=batch_size,
        workers=workers,
        seed=seed + 1,
        verify_hashes=verify_image_hashes,
    )
    model = build_mobilenet_v3_small(
        weights=initial_weights.path if initial_weights else "none",
        expected_sha256=initial_weights.sha256 if initial_weights else None,
        weights_role="imagenet" if initial_weights else None,
    ).to(device)
    weight_values = torch.as_tensor(
        _class_weights(train_records), dtype=torch.float32, device=device
    )
    criterion = nn.CrossEntropyLoss(weight=weight_values)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(config.raw["training"]["learning_rate"]),
        weight_decay=float(config.raw["training"]["weight_decay"]),
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    use_amp = device.type == "cuda" and bool(config.raw["training"]["amp_on_cuda"])
    scaler = torch.amp.GradScaler("cuda", enabled=use_amp)
    if device.type == "cuda":
        torch.cuda.reset_peak_memory_stats(device)

    checkpoint_path = run_directory / "best-checkpoint.pt"
    last_checkpoint_path = run_directory / "last-checkpoint.pt"
    active_source_hashes = source_hashes(root, _source_paths(root))
    runtime_identity = _resume_runtime_identity(runtime_snapshot)
    history: list[dict[str, Any]] = []
    best_key: tuple[float, float, float] | None = None
    best_epoch = 0
    epochs_without_improvement = 0
    completed_epoch = 0
    previous_training_seconds = 0.0
    resumed_from_epoch: int | None = None
    patience = int(config.raw["training"]["early_stopping_patience"])
    if resume_checkpoint is not None:
        if initial_weights is None or run_id is None:
            raise AssertionError("Validated resume inputs are missing")
        resume_payload = torch.load(
            resume_checkpoint.resolve(strict=True), map_location="cpu", weights_only=True
        )
        if not isinstance(resume_payload, dict):
            raise ValueError("Resume checkpoint payload must be an object")
        _validate_resume_payload(
            resume_payload,
            config=config,
            manifests=manifests,
            run_id=run_id,
            initial_weights=initial_weights,
            source_files=active_source_hashes,
            runtime_identity=runtime_identity,
            epochs=epochs,
            best_checkpoint_path=checkpoint_path,
        )
        model.load_state_dict(resume_payload["model_state_dict"], strict=True)
        optimizer.load_state_dict(resume_payload["optimizer_state_dict"])
        scheduler.load_state_dict(resume_payload["scheduler_state_dict"])
        scaler.load_state_dict(resume_payload["scaler_state_dict"])
        history = list(resume_payload["history"])
        raw_best_key = resume_payload["best_key"]
        best_key = tuple(float(value) for value in raw_best_key)
        if len(best_key) != 3:
            raise ValueError("Resume checkpoint best_key is invalid")
        best_epoch = int(resume_payload["best_epoch"])
        epochs_without_improvement = int(
            resume_payload["epochs_without_improvement"]
        )
        completed_epoch = int(resume_payload["completed_epoch"])
        previous_training_seconds = float(
            resume_payload.get("training_seconds_completed", 0.0)
        )
        _restore_rng_state(torch, resume_payload["rng_state"])
        train_loader.generator.set_state(resume_payload["train_generator_state"])
        validation_loader.generator.set_state(
            resume_payload["validation_generator_state"]
        )
        resumed_from_epoch = completed_epoch
        print(
            f"Reprise validée après l'époque {completed_epoch}; "
            f"prochaine époque: {completed_epoch + 1}/{epochs}",
            file=sys.stderr,
            flush=True,
        )

    started = time.perf_counter()
    for epoch in range(completed_epoch + 1, epochs + 1):
        if mode is RunMode.VALIDATION and epochs_without_improvement >= patience:
            break
        model.train()
        train_losses: list[float] = []
        for images, targets in train_loader:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, enabled=use_amp):
                logits = model(images)
                loss = criterion(logits, targets)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            train_losses.append(float(loss.detach().cpu()))
        validation_loss, labels, probabilities, _elapsed = _evaluate_loader(
            model, validation_loader, device=device, criterion=criterion
        )
        fixed_metrics = binary_metrics(
            labels,
            probabilities,
            0.5,
            ece_bins=int(config.raw["evaluation"]["ece_bins"]),
        )
        macro_f1 = float(fixed_metrics["macro_f1"])
        balanced = float(fixed_metrics["balanced_accuracy"])
        key = (macro_f1, balanced, -validation_loss)
        history.append(
            {
                "epoch": epoch,
                "learning_rate": optimizer.param_groups[0]["lr"],
                "train_loss": float(np.mean(train_losses)),
                "validation_loss": validation_loss,
                "validation_macro_f1_at_0_5": macro_f1,
                "validation_balanced_accuracy_at_0_5": balanced,
            }
        )
        improved = best_key is None or key > best_key
        if improved:
            best_key = key
            best_epoch = epoch
            epochs_without_improvement = 0
            _save_checkpoint(
                checkpoint_path,
                {
                    "schema_version": 1,
                    "experiment_id": config.experiment_id,
                    "architecture": "mobilenet_v3_small",
                    "state_dict": model.state_dict(),
                    "epoch": epoch,
                    "validation_macro_f1_at_0_5": macro_f1,
                    "config_sha256": config.sha256,
                    "train_validation_manifest_sha256": manifests.train_validation.sha256,
                    "initial_weights_sha256": (
                        initial_weights.sha256 if initial_weights else None
                    ),
                },
                torch,
            )
        else:
            epochs_without_improvement += 1
        scheduler.step()
        completed_epoch = epoch
        training_seconds_completed = (
            previous_training_seconds + time.perf_counter() - started
        )
        _save_checkpoint(
            last_checkpoint_path,
            {
                "schema_version": 2,
                "checkpoint_kind": "training-resume",
                "experiment_id": config.experiment_id,
                "architecture": "mobilenet_v3_small",
                "mode": mode.value,
                "run_id": run_directory.name,
                "config_sha256": config.sha256,
                "train_validation_manifest_sha256": manifests.train_validation.sha256,
                "initial_weights_sha256": (
                    initial_weights.sha256 if initial_weights else None
                ),
                "source_files": active_source_hashes,
                "runtime_identity": runtime_identity,
                "completed_epoch": completed_epoch,
                "model_state_dict": model.state_dict(),
                "optimizer_state_dict": optimizer.state_dict(),
                "scheduler_state_dict": scheduler.state_dict(),
                "scaler_state_dict": scaler.state_dict(),
                "history": history,
                "best_key": best_key,
                "best_epoch": best_epoch,
                "best_checkpoint_sha256": sha256_file(checkpoint_path),
                "epochs_without_improvement": epochs_without_improvement,
                "training_seconds_completed": training_seconds_completed,
                "rng_state": _capture_rng_state(torch),
                "train_generator_state": train_loader.generator.get_state(),
                "validation_generator_state": validation_loader.generator.get_state(),
            },
            torch,
        )
        print(
            f"Époque {epoch:02d}/{epochs} | "
            f"train_loss={history[-1]['train_loss']:.6f} | "
            f"val_loss={validation_loss:.6f} | macro_f1={macro_f1:.4f} | "
            f"balanced_acc={balanced:.4f} | "
            f"lr={history[-1]['learning_rate']:.7f} | "
            f"meilleure={best_epoch} | patience={epochs_without_improvement}/{patience}",
            file=sys.stderr,
            flush=True,
        )
        if mode is RunMode.VALIDATION and epochs_without_improvement >= patience:
            print(
                f"Early stopping après l'époque {epoch}: "
                f"aucune amélioration pendant {patience} époques.",
                file=sys.stderr,
                flush=True,
            )
            break

    training_seconds = previous_training_seconds + time.perf_counter() - started
    checkpoint = torch.load(
        checkpoint_path, map_location="cpu", weights_only=True
    )
    model.load_state_dict(checkpoint["state_dict"], strict=True)
    model.to(device)
    validation_loss, labels, probabilities, evaluation_seconds = _evaluate_loader(
        model, validation_loader, device=device, criterion=criterion
    )
    evaluation_config = config.raw["evaluation"]
    thresholds = np.linspace(
        float(evaluation_config["threshold_grid_start"]),
        float(evaluation_config["threshold_grid_stop"]),
        int(evaluation_config["threshold_grid_steps"]),
    )
    threshold, selected_metrics = select_threshold(
        labels,
        probabilities,
        thresholds=thresholds,
        ece_bins=int(evaluation_config["ece_bins"]),
    )
    fixed_metrics = binary_metrics(
        labels, probabilities, 0.5, ece_bins=int(evaluation_config["ece_bins"])
    )
    slices = _image_slices(validation_records, resolved_image_root)
    slice_metrics = {
        name: metrics_by_slice(
            labels,
            probabilities,
            values,
            threshold,
            ece_bins=int(evaluation_config["ece_bins"]),
        )
        for name, values in slices.items()
    }
    bootstrap = bootstrap_metrics_by_group(
        labels,
        probabilities,
        [record.acquisition_prefix for record in validation_records],
        threshold,
        iterations=(
            min(100, int(evaluation_config["bootstrap_iterations"]))
            if mode is RunMode.SMOKE
            else int(evaluation_config["bootstrap_iterations"])
        ),
        seed=seed,
        ece_bins=int(evaluation_config["ece_bins"]),
    )

    history_path = run_directory / "history.csv"
    predictions_path = run_directory / "validation-predictions.csv"
    curves_path = run_directory / "learning-curves.png"
    confusion_path = run_directory / "validation-confusion.png"
    environment_path = run_directory / "environment.json"
    source_hashes_path = run_directory / "source-hashes.json"
    _write_history(history_path, history)
    _write_predictions(predictions_path, validation_records, probabilities, threshold)
    _plot_history(curves_path, history)
    _plot_confusion(
        confusion_path,
        selected_metrics["confusion_matrix"],
        "Validation · seuil sélectionné",
    )
    runtime_details = {
        **environment_snapshot(device=device_name),
        **runtime_snapshot,
        "git": git_state(root),
    }
    write_json_atomic(environment_path, runtime_details)
    hashed_sources = active_source_hashes
    write_json_atomic(source_hashes_path, hashed_sources)
    peak_memory = (
        int(torch.cuda.max_memory_allocated(device)) if device.type == "cuda" else None
    )
    report = {
        "schema_version": 1,
        "experiment_id": config.experiment_id,
        "run_id": run_directory.name,
        "mode": mode.value,
        "benchmark_eligible": mode is RunMode.VALIDATION and verify_image_hashes,
        "generated_at_utc": utc_now(),
        "target": config.raw["dataset"]["target"],
        "config": {
            "path": relative_project_path(root, config.path, field="CNN config"),
            "sha256": config.sha256,
        },
        "split": {
            "lock_sha256": manifests.split_lock.sha256,
            "train_validation_manifest_sha256": manifests.train_validation.sha256,
            "test_manifest_opened": False,
        },
        "data": {
            "train_images": len(train_records),
            "validation_images": len(validation_records),
            "train_groups": len({record.acquisition_prefix for record in train_records}),
            "validation_groups": len(
                {record.acquisition_prefix for record in validation_records}
            ),
            "image_hashes_verified": verify_image_hashes,
            "image_root": _display_path(root, resolved_image_root),
        },
        "initialization": {"kind": "random", "external_weights": False},
        "training": {
            "seed": seed,
            "requested_epochs": epochs,
            "completed_epochs": len(history),
            "batch_size": batch_size,
            "workers": workers,
            "device": device_name,
            "amp": use_amp,
            "duration_seconds": training_seconds,
            "peak_cuda_memory_bytes": peak_memory,
            "resumed": resumed_from_epoch is not None,
            "resumed_from_epoch": resumed_from_epoch,
        },
        "selection": {
            "checkpoint_metric": "validation macro_f1 at threshold 0.5",
            "best_epoch": best_epoch,
            "threshold": threshold,
            "threshold_selected_on": "validation",
            "fixed_threshold_metrics": fixed_metrics,
            "selected_threshold_metrics": selected_metrics,
            "validation_loss": validation_loss,
        },
        "validation": {
            "metrics": selected_metrics,
            "group_bootstrap": bootstrap,
            "slices": slice_metrics,
            "evaluation_seconds": evaluation_seconds,
            "seconds_per_image": evaluation_seconds / len(validation_records),
        },
        "history": history,
        "source_files": hashed_sources,
        "environment": runtime_details,
        "warnings": [
            "The target is dataset image quality, not toxicity, diagnosis, or treatment efficacy.",
            "Acquisition mode and resolution are known target-correlated shortcuts.",
            "The YYMMDD group is an acquisition-date heuristic, not a documented biological unit.",
            "Smoke results are technical checks and must never be reported as "
            "benchmark performance.",
        ],
        "artifacts": {
            "checkpoint": artifact_record(root, checkpoint_path),
            "resume_checkpoint": artifact_record(root, last_checkpoint_path),
            "history": artifact_record(root, history_path),
            "predictions": artifact_record(root, predictions_path),
            "learning_curves": artifact_record(root, curves_path),
            "confusion_matrix": artifact_record(root, confusion_path),
            "environment": artifact_record(root, environment_path),
            "source_hashes": artifact_record(root, source_hashes_path),
        },
    }
    if initial_weights:
        report["initialization"] = {
            "kind": "local_pretrained_state_dict",
            "path": _display_path(root, initial_weights.path),
            "sha256": initial_weights.sha256,
            "metadata_path": _display_path(root, initial_weights.metadata_path),
            "metadata_sha256": initial_weights.metadata_sha256,
            "architecture": initial_weights.architecture,
            "weight_enum": initial_weights.weight_enum,
            "source_url": initial_weights.source_url,
            "license": initial_weights.license,
            "external_weights": True,
        }
    report_path = run_directory / "validation-report.json"
    generated_path = config.generated_reports_directory / f"{run_directory.name}.json"
    report["report_paths"] = {
        "run": relative_project_path(root, report_path, field="run report"),
        "generated": relative_project_path(root, generated_path, field="generated report"),
    }
    write_json_atomic(report_path, report)
    write_json_atomic(generated_path, report)
    return report


def run_final_evaluation(
    *,
    project_root: Path,
    image_root: Path | None,
    config: ExperimentConfig,
    manifests: RunManifests,
    frozen: FrozenManifest,
    device_name: str,
    runtime_snapshot: dict[str, Any],
    run_id: str | None = None,
    verify_image_hashes: bool = True,
) -> dict[str, Any]:
    if manifests.mode is not RunMode.FINAL_EVAL or manifests.test is None:
        raise ValueError("Final evaluation requires an authorized test manifest")
    if device_name != "cuda":
        raise ValueError("Final evaluation requires CUDA")
    if not verify_image_hashes:
        raise ValueError("Final evaluation requires image hash verification")
    root = project_root.resolve()
    resolved_image_root = (image_root or root).resolve()
    if not resolved_image_root.is_dir():
        raise ValueError("CNN image root is missing or not a directory")
    torch, nn, _loader = _import_torch()
    seed = int(config.raw["training"]["seed"])
    _seed_everything(torch, seed)
    device = torch.device(device_name)
    run_directory = _prepare_run_directory(config, RunMode.FINAL_EVAL, run_id)
    records = list(manifests.test.records)
    loader = _make_loader(
        records,
        image_root=resolved_image_root,
        training=False,
        batch_size=int(config.raw["training"]["batch_size"]),
        workers=int(config.raw["training"]["workers"]),
        seed=seed,
        verify_hashes=verify_image_hashes,
    )
    checkpoint = frozen.artifacts["checkpoint"]
    model = build_mobilenet_v3_small(
        weights=checkpoint.path,
        expected_sha256=checkpoint.sha256,
        weights_role="checkpoint",
    ).to(device)
    criterion = nn.CrossEntropyLoss()
    loss, labels, probabilities, evaluation_seconds = _evaluate_loader(
        model, loader, device=device, criterion=criterion
    )
    evaluation = config.raw["evaluation"]
    threshold = frozen.threshold
    metrics = binary_metrics(
        labels, probabilities, threshold, ece_bins=int(evaluation["ece_bins"])
    )
    slices = _image_slices(records, resolved_image_root)
    slice_metrics = {
        name: metrics_by_slice(
            labels,
            probabilities,
            values,
            threshold,
            ece_bins=int(evaluation["ece_bins"]),
        )
        for name, values in slices.items()
    }
    bootstrap = bootstrap_metrics_by_group(
        labels,
        probabilities,
        [record.acquisition_prefix for record in records],
        threshold,
        iterations=int(evaluation["bootstrap_iterations"]),
        seed=seed,
        ece_bins=int(evaluation["ece_bins"]),
    )
    predictions_path = run_directory / "test-predictions.csv"
    confusion_path = run_directory / "test-confusion.png"
    _write_predictions(predictions_path, records, probabilities, threshold)
    _plot_confusion(confusion_path, metrics["confusion_matrix"], "Test final gelé")
    report = {
        "schema_version": 1,
        "experiment_id": config.experiment_id,
        "run_id": run_directory.name,
        "mode": RunMode.FINAL_EVAL.value,
        "benchmark_eligible": True,
        "generated_at_utc": utc_now(),
        "protocol": {
            "training_performed": False,
            "model_selection_performed": False,
            "threshold_selection_performed": False,
            "threshold_source": "frozen validation manifest",
            "test_access_receipt": (
                relative_project_path(
                    root, manifests.test_access_receipt, field="test access receipt"
                )
                if manifests.test_access_receipt
                else None
            ),
        },
        "config": {
            "path": relative_project_path(root, config.path, field="CNN config"),
            "sha256": config.sha256,
        },
        "frozen_manifest": {
            "path": relative_project_path(root, frozen.path, field="frozen manifest"),
            "sha256": frozen.sha256,
        },
        "test": {
            "images": len(records),
            "groups": len({record.acquisition_prefix for record in records}),
            "manifest_sha256": manifests.test.sha256,
            "image_hashes_verified": verify_image_hashes,
            "image_root": _display_path(root, resolved_image_root),
            "loss": loss,
            "threshold": threshold,
            "metrics": metrics,
            "group_bootstrap": bootstrap,
            "slices": slice_metrics,
            "evaluation_seconds": evaluation_seconds,
            "seconds_per_image": evaluation_seconds / len(records),
        },
        "environment": {**environment_snapshot(device=device_name), **runtime_snapshot},
        "artifacts": {
            "checkpoint": artifact_record(root, checkpoint.path),
            "predictions": artifact_record(root, predictions_path),
            "confusion_matrix": artifact_record(root, confusion_path),
        },
        "warnings": [
            "This is the single frozen test estimate and must not drive a new model decision.",
            "The target is dataset image quality, not a biological or clinical conclusion.",
        ],
    }
    report_path = run_directory / "final-test-report.json"
    generated_path = config.generated_reports_directory / f"{run_directory.name}.json"
    report["report_paths"] = {
        "run": relative_project_path(root, report_path, field="final report"),
        "generated": relative_project_path(root, generated_path, field="generated report"),
    }
    write_json_atomic(report_path, report)
    write_json_atomic(generated_path, report)
    return report
