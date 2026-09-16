"""Validation of explicitly supplied, offline CNN initialization weights."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from training.ooc_cnn.manifests import sha256_file, validate_sha256

EXPECTED_ARCHITECTURE = "mobilenet_v3_small"
EXPECTED_WEIGHT_ENUM = "MobileNet_V3_Small_Weights.IMAGENET1K_V1"
EXPECTED_SOURCE_URL = (
    "https://download.pytorch.org/models/mobilenet_v3_small-047dcff4.pth"
)


@dataclass(frozen=True)
class InitialWeights:
    path: Path
    sha256: str
    metadata_path: Path
    metadata_sha256: str
    architecture: str
    weight_enum: str
    source_url: str
    license: str


def load_initial_weights(
    *,
    weights_path: Path,
    expected_sha256: str,
    metadata_path: Path,
) -> InitialWeights:
    expected = validate_sha256(expected_sha256, "initial weights sha256")
    if not weights_path.is_file():
        raise ValueError(f"Initial weights file is missing: {weights_path}")
    if sha256_file(weights_path) != expected:
        raise ValueError("Initial weights checksum mismatch")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError("Initial weights metadata is not valid JSON") from error
    if not isinstance(metadata, dict) or metadata.get("schema_version") != 1:
        raise ValueError("Initial weights metadata must use schema_version 1")
    if metadata.get("file_sha256") != expected:
        raise ValueError("Initial weights metadata checksum does not match the file")
    expected_name = metadata.get("file_name")
    if not isinstance(expected_name, str) or expected_name != weights_path.name:
        raise ValueError("Initial weights metadata file name does not match")
    required = ("architecture", "weight_enum", "source_url", "license")
    if any(
        not isinstance(metadata.get(name), str) or not metadata[name].strip()
        for name in required
    ):
        raise ValueError("Initial weights metadata is incomplete")
    if metadata["architecture"] != EXPECTED_ARCHITECTURE:
        raise ValueError("Initial weights architecture must be mobilenet_v3_small")
    if metadata["weight_enum"] != EXPECTED_WEIGHT_ENUM:
        raise ValueError("Initial weights must use the pinned torchvision weight enum")
    if metadata["source_url"] != EXPECTED_SOURCE_URL:
        raise ValueError("Initial weights source URL does not match the pinned artifact")
    return InitialWeights(
        path=weights_path.resolve(),
        sha256=expected,
        metadata_path=metadata_path.resolve(),
        metadata_sha256=sha256_file(metadata_path),
        architecture=metadata["architecture"],
        weight_enum=metadata["weight_enum"],
        source_url=metadata["source_url"],
        license=metadata["license"],
    )
