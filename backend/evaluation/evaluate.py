"""Evaluation entry point for reproducible competition metrics."""

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate OrganChip Insight models")
    parser.add_argument("--config", required=True, help="Path to an approved evaluation config")
    args = parser.parse_args()
    raise SystemExit(
        f"Evaluation config '{args.config}' is not implemented yet. "
        "Complete the dataset audit and metric selection first."
    )


if __name__ == "__main__":
    main()

