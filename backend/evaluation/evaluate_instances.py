"""Run a versioned instance-segmentation and counting benchmark."""

import argparse
import json
from pathlib import Path

from app.instance_benchmark import evaluate_instance_config

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    arguments = parser.parse_args()
    config_path = (
        arguments.config
        if arguments.config.is_absolute()
        else PROJECT_ROOT / arguments.config
    )
    report = evaluate_instance_config(config_path.resolve(), PROJECT_ROOT)
    print(json.dumps(report["results"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
