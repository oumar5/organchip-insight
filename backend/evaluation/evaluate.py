"""Run a versioned foreground-segmentation benchmark."""

import argparse
import json
from pathlib import Path

from app.benchmark import evaluate_config

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate OrganChip Insight models")
    parser.add_argument("--config", required=True, type=Path, help="Evaluation config path")
    args = parser.parse_args()
    config_path = args.config if args.config.is_absolute() else PROJECT_ROOT / args.config
    report = evaluate_config(config_path.resolve(), PROJECT_ROOT)
    print(json.dumps(report["results"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
