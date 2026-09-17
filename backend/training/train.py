"""Training entry point reserved for the selected competition dataset.

This module intentionally refuses to invent a training run before the dataset,
labels, split policy and evaluation protocol are documented in docs/02-research/data-strategy.md.
"""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Train OrganChip Insight models")
    parser.add_argument("--config", required=True, help="Path to an approved training config")
    args = parser.parse_args()
    raise SystemExit(
        f"Training config '{args.config}' is not implemented yet. "
        "Complete the dataset audit and split protocol first."
    )


if __name__ == "__main__":
    main()

