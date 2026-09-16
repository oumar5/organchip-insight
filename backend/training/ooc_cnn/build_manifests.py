"""CLI for deriving physically separated CNN manifests from the frozen OoC split."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from training.ooc_cnn.manifests import CANONICAL_SPLIT_SHA256, build_separated_manifests

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        type=Path,
        default=PROJECT_ROOT / "data/splits/ooc-grouped-v1.csv",
    )
    parser.add_argument(
        "--expected-source-sha256",
        default=CANONICAL_SPLIT_SHA256,
    )
    parser.add_argument(
        "--train-validation-output",
        type=Path,
        default=PROJECT_ROOT / "data/splits/ooc-grouped-v1-train-validation.csv",
    )
    parser.add_argument(
        "--test-output",
        type=Path,
        default=PROJECT_ROOT / "data/splits/ooc-grouped-v1-test.csv",
    )
    parser.add_argument(
        "--lock-output",
        type=Path,
        default=PROJECT_ROOT / "data/splits/ooc-grouped-v1-lock.json",
    )
    return parser


def main() -> None:
    args = _parser().parse_args()
    lock = build_separated_manifests(
        project_root=PROJECT_ROOT,
        source_path=args.source,
        expected_source_sha256=args.expected_source_sha256,
        train_validation_path=args.train_validation_output,
        test_path=args.test_output,
        lock_path=args.lock_output,
    )
    print(json.dumps(lock, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
