"""Torch-independent protocol foundations for the OoC CNN experiments."""

from training.ooc_cnn.protocol import (
    FINAL_EVAL_CONFIRMATION,
    RunManifests,
    RunMode,
    load_run_manifests,
    validate_receipt_chain,
)

__all__ = [
    "FINAL_EVAL_CONFIRMATION",
    "RunManifests",
    "RunMode",
    "load_run_manifests",
    "validate_receipt_chain",
]
