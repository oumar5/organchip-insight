import argparse
import json
from pathlib import Path

from app.ml.pipeline import AdaptiveSegmentationAnalyzer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run zero-training microscopy inference on local images."
    )
    parser.add_argument("images", nargs="+", type=Path, help="PNG, JPEG or TIFF image paths")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/cli-inference"),
        help="Directory for overlays and result.json",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    missing = [str(path) for path in args.images if not path.is_file()]
    if missing:
        raise SystemExit(f"Missing input image(s): {', '.join(missing)}")

    analyzer = AdaptiveSegmentationAnalyzer()
    output = analyzer.analyze(
        args.images,
        artifact_dir=args.output_dir,
        artifact_url_prefix=".",
    )
    payload = {
        "analysis_version": analyzer.version,
        "engine": analyzer.engine.model_dump(mode="json"),
        "metrics": output.metrics,
        "image_results": [item.model_dump(mode="json") for item in output.image_results],
        "artifacts": [item.model_dump(mode="json") for item in output.artifacts],
        "warnings": output.warnings,
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result_path = args.output_dir / "result.json"
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(result_path)


if __name__ == "__main__":
    main()
