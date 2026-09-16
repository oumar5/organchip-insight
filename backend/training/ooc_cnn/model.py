"""Lazy construction of the binary MobileNetV3 Small classifier."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_weights_path(
    weights: str | Path,
    expected_sha256: str | None,
) -> Path | None:
    if weights == "none":
        if expected_sha256 is not None:
            raise ValueError("expected_sha256 must be omitted when weights='none'")
        return None

    path = Path(weights).expanduser().resolve(strict=False)
    if not path.is_file():
        raise FileNotFoundError(f"local weights file is missing: {path}")
    if expected_sha256 is None:
        raise ValueError("expected_sha256 is required for local weights")
    normalized_sha256 = expected_sha256.lower()
    if SHA256_PATTERN.fullmatch(normalized_sha256) is None:
        raise ValueError("expected_sha256 must contain 64 hexadecimal characters")
    actual_sha256 = _sha256(path)
    if actual_sha256 != normalized_sha256:
        raise ValueError(
            f"weights checksum mismatch: expected {normalized_sha256}, got {actual_sha256}"
        )
    return path


def _load_state_dict(torch: Any, path: Path) -> Mapping[str, Any]:
    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    except TypeError as error:
        raise RuntimeError(
            "this PyTorch version cannot safely load local weights with weights_only=True"
        ) from error
    if isinstance(checkpoint, Mapping):
        for key in ("state_dict", "model_state_dict", "model"):
            if isinstance(checkpoint.get(key), Mapping):
                checkpoint = checkpoint[key]
                break
    if not isinstance(checkpoint, Mapping):
        raise ValueError("local weights must contain a PyTorch state dictionary")
    return checkpoint


def build_mobilenet_v3_small(
    *,
    weights: str | Path = "none",
    expected_sha256: str | None = None,
    weights_role: Literal["imagenet", "checkpoint"] | None = None,
    dropout: float = 0.2,
) -> Any:
    """Build a two-logit model without ever asking torchvision to download weights."""
    if not 0 <= dropout < 1:
        raise ValueError("dropout must be in the interval [0, 1)")
    weights_path = _validated_weights_path(weights, expected_sha256)
    if weights_path is None and weights_role is not None:
        raise ValueError("weights_role must be omitted when weights='none'")
    if weights_path is not None and weights_role is None:
        raise ValueError("weights_role is required for local weights")

    try:
        import torch
        from torch import nn
        from torchvision.models import mobilenet_v3_small
    except (ImportError, RuntimeError) as error:
        raise RuntimeError(
            "torch and torchvision are required to build the CNN model"
        ) from error

    model = mobilenet_v3_small(weights=None, dropout=dropout)
    state_dict = _load_state_dict(torch, weights_path) if weights_path else None
    final_layer = model.classifier[-1]
    if not isinstance(final_layer, nn.Linear):
        raise TypeError("unexpected torchvision MobileNetV3 classifier layout")

    output_classes: int | None = None
    if state_dict is not None:
        output_weight = state_dict.get("classifier.3.weight")
        output_classes = int(output_weight.shape[0]) if output_weight is not None else None
        expected_classes = 1000 if weights_role == "imagenet" else 2
        if output_classes != expected_classes:
            raise ValueError(
                f"local {weights_role} weights must have {expected_classes} output classes"
            )
        if weights_role == "imagenet":
            model.load_state_dict(state_dict, strict=True)

    model.classifier[-1] = nn.Linear(final_layer.in_features, 2)

    if state_dict is not None and weights_role == "checkpoint":
        model.load_state_dict(state_dict, strict=True)
    return model
