"""Verify the integrity and test-access policy of local CNN experiment artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS = (
    "kaggle-validation-campaign-v2-gray224",
    "kaggle-validation-campaign-v2-gray448",
)
REQUIRED_FILES = {
    "artifact-manifest.json",
    "best-checkpoint.pt",
    "environment.json",
    "frozen-selection.json",
    "history.csv",
    "learning-curves.png",
    "onnx/export-report.json",
    "onnx/labels.json",
    "onnx/model.onnx",
    "onnx/preprocessing.json",
    "validation-confusion.png",
    "validation-predictions.csv",
    "validation-report.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Invalid JSON artifact: {path}") from error
    if not isinstance(payload, dict):
        raise ValueError(f"JSON artifact must be an object: {path}")
    return payload


def verify_reference(reference: dict[str, Any], *, label: str) -> None:
    raw_path = reference.get("path")
    expected = reference.get("sha256")
    if not isinstance(raw_path, str) or not isinstance(expected, str):
        raise ValueError(f"Incomplete artifact reference: {label}")
    path = REPOSITORY_ROOT / raw_path
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"Missing or unsafe artifact: {raw_path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"SHA-256 mismatch for {label}: {raw_path}")


def audit_run(run_id: str) -> dict[str, Any]:
    root = REPOSITORY_ROOT / "data/experiments/ooc-cnn" / run_id
    if not root.is_dir() or root.is_symlink():
        raise ValueError(f"Missing or unsafe run directory: {root}")
    for relative in REQUIRED_FILES:
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Required run artifact is missing or unsafe: {path}")

    manifest = read_json(root / "artifact-manifest.json")
    if manifest.get("schema_version") != 2 or manifest.get("run_id") != run_id:
        raise ValueError(f"Invalid artifact manifest identity: {run_id}")
    records = manifest.get("files")
    if not isinstance(records, list) or manifest.get("file_count") != len(records):
        raise ValueError(f"Invalid artifact manifest file count: {run_id}")
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"Invalid artifact record: {run_id}")
        relative = record.get("path")
        if not isinstance(relative, str):
            raise ValueError(f"Invalid artifact path: {run_id}")
        path = root / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Manifest artifact is missing or unsafe: {path}")
        if path.stat().st_size != record.get("size_bytes"):
            raise ValueError(f"Size mismatch: {path}")
        if sha256_file(path) != record.get("sha256"):
            raise ValueError(f"SHA-256 mismatch: {path}")

    frozen = read_json(root / "frozen-selection.json")
    policy = frozen.get("policy")
    selection = frozen.get("selection")
    if not isinstance(policy, dict) or not isinstance(selection, dict):
        raise ValueError(f"Frozen-selection contract is incomplete: {run_id}")
    if policy.get("selection_split") != "validation":
        raise ValueError(f"Selection did not use validation only: {run_id}")
    if policy.get("test_used_for_selection") is not False:
        raise ValueError(f"Frozen test was used for selection: {run_id}")
    if policy.get("test_manifest_opened_while_freezing") is not False:
        raise ValueError(f"Frozen test manifest was opened while freezing: {run_id}")
    if selection.get("threshold_selected_on") != "validation":
        raise ValueError(f"Threshold was not selected on validation: {run_id}")
    artifacts = frozen.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError(f"Frozen-selection artifact map is missing: {run_id}")
    for label, reference in artifacts.items():
        if not isinstance(reference, dict):
            raise ValueError(f"Invalid frozen artifact reference: {run_id}/{label}")
        verify_reference(reference, label=f"{run_id}/{label}")

    report = read_json(root / "validation-report.json")
    data = report.get("data")
    if report.get("mode") != "validation" or report.get("benchmark_eligible") is not True:
        raise ValueError(f"Validation report is not benchmark-eligible: {run_id}")
    if not isinstance(data, dict) or data.get("image_hashes_verified") is not True:
        raise ValueError(f"Validation image hashes were not verified: {run_id}")
    export = read_json(root / "onnx/export-report.json")
    export_contract = export.get("export")
    if not isinstance(export_contract, dict) or export_contract.get("parity_passed") is not True:
        raise ValueError(f"ONNX parity did not pass: {run_id}")
    return {
        "run_id": run_id,
        "files_verified": len(records),
        "best_epoch": selection.get("best_epoch"),
        "threshold": selection.get("threshold"),
        "onnx_parity_passed": True,
        "test_used_for_selection": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_ids", nargs="*", default=list(DEFAULT_RUNS))
    arguments = parser.parse_args()
    test_receipts = list(
        (REPOSITORY_ROOT / "data/experiments").rglob("*test*access*receipt*.json")
    )
    if test_receipts:
        raise ValueError(f"Frozen-test access receipt found: {test_receipts[0]}")
    results = [audit_run(run_id) for run_id in arguments.run_ids]
    print(
        json.dumps(
            {
                "status": "ok",
                "runs": results,
                "frozen_test_access_receipts": 0,
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
