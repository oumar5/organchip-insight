"""Fail-closed validation of the isolated CNN runtime contract."""

from __future__ import annotations

import importlib.metadata
import json
import platform
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from packaging.specifiers import SpecifierSet
from packaging.version import Version

from training.ooc_cnn.manifests import sha256_file, validate_sha256
from training.ooc_cnn.protocol import RunMode


def _distribution_version(name: str) -> str:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError as error:
        raise RuntimeError(f"Required CNN runtime package is missing: {name}") from error


def _version_matches_pattern(version: str, pattern: str) -> bool:
    if not pattern.endswith(".*"):
        return version == pattern
    return Version(version).release[:2] == Version(pattern[:-2]).release[:2]


def _pip_freeze() -> list[str]:
    values = {
        f"{distribution.metadata['Name']}=={distribution.version}"
        for distribution in importlib.metadata.distributions()
        if distribution.metadata.get("Name")
    }
    return sorted(values, key=str.lower)


def _load_contract(contract_path: Path, expected_sha256: str) -> dict[str, Any]:
    expected = validate_sha256(expected_sha256, "runtime contract expected_sha256")
    if sha256_file(contract_path) != expected:
        raise RuntimeError("CNN runtime contract checksum mismatch")
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError("CNN runtime contract is not valid JSON") from error
    if not isinstance(contract, dict) or contract.get("schema_version") != 1:
        raise RuntimeError("CNN runtime contract must use schema_version 1")
    return contract


def _required_hash_names(
    contract: dict[str, Any], run_mode: RunMode
) -> tuple[str, ...]:
    required_hashes = contract.get("required_hashes")
    if not isinstance(required_hashes, dict):
        raise RuntimeError("CNN runtime required-hash contract is invalid")
    names: list[str] = []
    for section in ("all_modes", run_mode.value):
        values = required_hashes.get(section, [])
        if (
            not isinstance(values, list)
            or not all(isinstance(value, str) and value for value in values)
        ):
            raise RuntimeError(f"CNN runtime required hashes are invalid: {section}")
        names.extend(values)
    if len(set(names)) != len(names):
        raise RuntimeError("CNN runtime required hashes contain duplicates")
    return tuple(names)


def validate_required_hashes(
    *,
    contract_path: Path,
    expected_sha256: str,
    mode: RunMode | str,
    provided_hashes: Mapping[str, object],
) -> dict[str, str]:
    """Validate that every mode-required digest is explicitly present and shaped."""

    contract = _load_contract(contract_path, expected_sha256)
    preflight = contract.get("preflight")
    if not isinstance(preflight, dict) or preflight.get(
        "fail_if_required_hash_missing"
    ) is not True:
        raise RuntimeError("CNN runtime required-hash preflight policy is invalid")
    run_mode = RunMode(mode)
    required_names = _required_hash_names(contract, run_mode)
    missing = [name for name in required_names if name not in provided_hashes]
    if missing:
        raise RuntimeError(
            "CNN runtime required hashes are missing: " + ", ".join(missing)
        )
    return {
        name: validate_sha256(provided_hashes[name], f"required hash {name}")
        for name in required_names
    }


def validate_runtime_contract(
    *,
    contract_path: Path,
    expected_sha256: str,
    mode: RunMode | str,
    requested_device: str,
) -> tuple[str, dict[str, Any]]:
    contract = _load_contract(contract_path, expected_sha256)
    if contract.get("execution_policy") != {
        "internet_required": False,
        "network_installation_allowed": False,
        "implicit_model_downloads_allowed": False,
        "test_access_receipt_scope": "workspace",
        "test_manifest_access_modes": ["final-eval"],
    }:
        raise RuntimeError("CNN runtime execution policy is invalid")
    run_mode = RunMode(mode)
    mode_contract = contract.get("modes", {}).get(run_mode.value)
    runtime = contract.get("runtime")
    if not isinstance(mode_contract, dict) or not isinstance(runtime, dict):
        raise RuntimeError("CNN runtime contract is incomplete")
    preflight = contract.get("preflight")
    boolean_flags = (
        "fail_if_network_installation_requested",
        "fail_if_implicit_weight_download_requested",
        "fail_if_required_hash_missing",
        "fail_if_hash_mismatch",
        "fail_if_torchvision_pair_unlisted",
    )
    if not isinstance(preflight, dict) or any(
        preflight.get(name) is not True for name in boolean_flags
    ):
        raise RuntimeError("CNN runtime preflight policy is invalid")
    if preflight.get("fail_if_gpu_missing_in_modes") != [
        "validation",
        "final-eval",
    ]:
        raise RuntimeError("CNN runtime GPU preflight policy is invalid")
    initial_weights_modes = (
        contract.get("local_inputs", {})
        .get("initial_weights", {})
        .get("required_for_modes")
    )
    if initial_weights_modes != ["validation"]:
        raise RuntimeError("CNN runtime initial-weight input policy is invalid")
    weights_required = run_mode is RunMode.VALIDATION
    if mode_contract.get("pretrained_weights_required") is not weights_required:
        raise RuntimeError("CNN runtime pretrained-weight policy is invalid")
    if run_mode is RunMode.FINAL_EVAL and mode_contract.get(
        "test_access_receipt_scope"
    ) != "workspace":
        raise RuntimeError("CNN runtime final receipt scope is invalid")
    required_hash_names = _required_hash_names(contract, run_mode)

    python_specifier = runtime.get("python", {}).get("specifier")
    if not isinstance(python_specifier, str) or Version(
        platform.python_version()
    ) not in SpecifierSet(python_specifier):
        raise RuntimeError("Python version does not satisfy the CNN runtime contract")

    package_contracts = runtime.get("packages")
    if not isinstance(package_contracts, dict):
        raise RuntimeError("CNN package runtime contract is invalid")
    installed: dict[str, str] = {}
    for name, package_contract in package_contracts.items():
        if not isinstance(package_contract, dict):
            raise RuntimeError(f"CNN package contract is invalid: {name}")
        specifier = package_contract.get("specifier")
        if not isinstance(specifier, str):
            raise RuntimeError(f"CNN package specifier is invalid: {name}")
        version = _distribution_version(name)
        if Version(version) not in SpecifierSet(specifier):
            raise RuntimeError(
                f"CNN runtime package {name}=={version} violates {specifier}"
            )
        installed[name] = version

    accepted_pairs = runtime.get("accepted_torch_torchvision_pairs")
    if not isinstance(accepted_pairs, list) or not any(
        isinstance(pair, dict)
        and isinstance(pair.get("torch"), str)
        and isinstance(pair.get("torchvision"), str)
        and _version_matches_pattern(installed["torch"], pair["torch"])
        and _version_matches_pattern(installed["torchvision"], pair["torchvision"])
        for pair in accepted_pairs
    ):
        raise RuntimeError("Torch and torchvision versions are not an accepted pair")

    try:
        import torch
    except (ImportError, RuntimeError) as error:
        raise RuntimeError("PyTorch is unavailable in the CNN runtime") from error
    requested = requested_device.lower()
    if requested not in {"auto", "cpu", "cuda"}:
        raise ValueError("CNN device must be auto, cpu, or cuda")
    cuda_available = bool(torch.cuda.is_available())
    resolved = "cuda" if requested == "auto" and cuda_available else requested
    if resolved == "auto":
        resolved = "cpu"
    allowed_devices = mode_contract.get("allowed_devices")
    if not isinstance(allowed_devices, list) or resolved not in allowed_devices:
        raise RuntimeError(f"Device {resolved} is forbidden for CNN mode {run_mode.value}")
    if resolved == "cuda" and not cuda_available:
        raise RuntimeError("CUDA was requested but is unavailable")
    if mode_contract.get("gpu_required") is True and resolved != "cuda":
        raise RuntimeError(f"CNN mode {run_mode.value} requires a CUDA GPU")

    gpu_names = (
        [torch.cuda.get_device_name(index) for index in range(torch.cuda.device_count())]
        if cuda_available
        else []
    )
    snapshot = {
        "contract_id": contract.get("contract_id"),
        "contract_sha256": expected_sha256,
        "mode": run_mode.value,
        "execution_policy": contract["execution_policy"],
        "declared_required_hashes": contract.get("required_hashes"),
        "required_hashes_for_mode": list(required_hash_names),
        "python": platform.python_version(),
        "packages": installed,
        "torch_cuda_version": torch.version.cuda,
        "cudnn_version": torch.backends.cudnn.version(),
        "cuda_available": cuda_available,
        "gpu_count": int(torch.cuda.device_count()) if cuda_available else 0,
        "gpu_names": gpu_names,
        "requested_device": requested,
        "resolved_device": resolved,
        "pip_freeze": _pip_freeze(),
    }
    return resolved, snapshot
