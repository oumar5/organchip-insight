import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from app.ml.pipeline import AdaptiveSegmentationAnalyzer

SUPPORTED_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validate_image_path(path: Path) -> Path:
    if path.is_symlink():
        raise ValueError(f"Symbolic links are not accepted: {path}")
    if not path.is_file():
        raise ValueError(f"Missing input image: {path}")
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        raise ValueError(f"Unsupported input extension: {path}")
    return path.resolve()


def _directory_images(directory: Path, *, recursive: bool) -> list[Path]:
    if directory.is_symlink():
        raise ValueError(f"Symbolic links are not accepted: {directory}")
    if not directory.is_dir():
        raise ValueError(f"Missing input directory: {directory}")
    entries = directory.rglob("*") if recursive else directory.iterdir()
    candidates: list[Path] = []
    for entry in sorted(entries):
        if entry.suffix.lower() not in SUPPORTED_SUFFIXES:
            continue
        candidates.append(_validate_image_path(entry))
    if not candidates:
        scope = "recursively" if recursive else "at its top level"
        raise ValueError(f"No supported images found {scope}: {directory}")
    return candidates


def _manifest_images(manifest_path: Path) -> list[Path]:
    if manifest_path.is_symlink():
        raise ValueError(f"Symbolic links are not accepted: {manifest_path}")
    if not manifest_path.is_file():
        raise ValueError(f"Missing input manifest: {manifest_path}")
    try:
        payload: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as error:
        raise ValueError(f"Invalid input manifest: {manifest_path}") from error
    if payload.get("schema_version") != 1 or not isinstance(payload.get("images"), list):
        raise ValueError("Input manifest must use schema_version 1 and contain images")

    root_value = payload.get("path_root", ".")
    if not isinstance(root_value, str):
        raise ValueError("Input manifest path_root must be a string")
    root = (manifest_path.parent / root_value).resolve()
    images: list[Path] = []
    for index, record in enumerate(payload["images"]):
        if not isinstance(record, dict):
            raise ValueError(f"Input manifest image #{index + 1} must be an object")
        relative_path = record.get("path")
        expected_sha256 = record.get("sha256")
        if not isinstance(relative_path, str) or not relative_path:
            raise ValueError(f"Input manifest image #{index + 1} has no path")
        if not isinstance(expected_sha256, str) or not SHA256_PATTERN.fullmatch(
            expected_sha256
        ):
            raise ValueError(f"Input manifest image #{index + 1} has an invalid SHA-256")
        unresolved = root / relative_path
        resolved = unresolved.resolve()
        if not resolved.is_relative_to(root):
            raise ValueError(f"Input manifest path escapes path_root: {relative_path}")
        current = root
        for part in Path(relative_path).parts:
            current /= part
            if current.is_symlink():
                raise ValueError(f"Symbolic links are not accepted: {unresolved}")
        image = _validate_image_path(unresolved)
        actual_sha256 = sha256_file(image)
        if actual_sha256 != expected_sha256:
            raise ValueError(
                f"Input image SHA-256 mismatch for {relative_path}: "
                f"expected {expected_sha256}, got {actual_sha256}"
            )
        images.append(image)
    if not images:
        raise ValueError("Input manifest contains no images")
    return images


def resolve_input_images(
    inputs: list[Path],
    input_directories: list[Path],
    manifest: Path | None,
    *,
    recursive: bool,
) -> list[Path]:
    images: list[Path] = []
    for source in inputs:
        if source.is_dir() and not source.is_symlink():
            images.extend(_directory_images(source, recursive=recursive))
        else:
            images.append(_validate_image_path(source))
    for directory in input_directories:
        images.extend(_directory_images(directory, recursive=recursive))
    if manifest is not None:
        images.extend(_manifest_images(manifest))
    if not images:
        raise ValueError("Provide at least one image, input directory, or manifest")

    unique: list[Path] = []
    seen: set[Path] = set()
    for image in images:
        if image not in seen:
            unique.append(image)
            seen.add(image)
    return unique


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run zero-training microscopy inference on local images."
    )
    parser.add_argument(
        "inputs",
        nargs="*",
        type=Path,
        help="PNG, JPEG or TIFF image paths, or directories",
    )
    parser.add_argument(
        "--input-dir",
        action="append",
        default=[],
        type=Path,
        help="Directory containing input images; may be repeated",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Versioned JSON manifest with paths and SHA-256 values",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Discover supported images recursively in input directories",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("artifacts/cli-inference"),
        help="Directory for overlays and result.json",
    )
    return parser.parse_args()


def run_inference(images: list[Path], output_dir: Path) -> Path:
    analyzer = AdaptiveSegmentationAnalyzer()
    output = analyzer.analyze(
        images,
        artifact_dir=output_dir,
        artifact_url_prefix=".",
    )
    payload = {
        "analysis_version": analyzer.version,
        "engine": analyzer.engine.model_dump(mode="json"),
        "input_files": [
            {"filename": path.name, "sha256": sha256_file(path)} for path in images
        ],
        "metrics": output.metrics,
        "image_results": [item.model_dump(mode="json") for item in output.image_results],
        "artifacts": [item.model_dump(mode="json") for item in output.artifacts],
        "warnings": output.warnings,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    result_path = output_dir / "result.json"
    result_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return result_path


def main() -> None:
    args = parse_args()
    try:
        images = resolve_input_images(
            args.inputs,
            args.input_dir,
            args.manifest,
            recursive=args.recursive,
        )
        result_path = run_inference(images, args.output_dir)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(result_path)


if __name__ == "__main__":
    main()
