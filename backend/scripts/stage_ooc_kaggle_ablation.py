"""Stage a private Kaggle GPU kernel for a pre-registered CNN ablation."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK_PATH = ROOT / "notebooks/ooc-cnn-kaggle.ipynb"
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
DATASET_SOURCES = (
    "oumarbenlol/organchip-insight-source-campaign-v2",
    "oumarbenlol/organchip-train-validation-v2",
    "oumarbenlol/organchip-cnn-offline-resources-v1",
)
VARIANTS = {
    "a": {
        "slug": "organchip-cnn-ablation-a-gray224",
        "title": "OrganChip CNN Ablation A - Grayscale 224",
        "run_id": "kaggle-validation-campaign-v2-gray224",
        "config": (
            "backend/training/configs/"
            "ooc-cnn-mobilenet-v3-small-campaign-v2-gray224.json"
        ),
    },
    "b": {
        "slug": "organchip-cnn-ablation-b-gray448",
        "title": "OrganChip CNN Ablation B - Grayscale 448",
        "run_id": "kaggle-validation-campaign-v2-gray448",
        "config": (
            "backend/training/configs/"
            "ooc-cnn-mobilenet-v3-small-campaign-v2-gray448.json"
        ),
    },
}


def _replace_assignment(source: str, name: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(name)} = .+$", flags=re.MULTILINE)
    replacement = f"{name} = {json.dumps(value)}"
    updated, count = pattern.subn(replacement, source)
    if count != 1:
        raise ValueError(f"Notebook must define {name} exactly once")
    return updated


def _replace_path_assignment(source: str, name: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(name)} = Path\(.+\)$", flags=re.MULTILINE)
    replacement = f"{name} = Path({json.dumps(value)})"
    updated, count = pattern.subn(replacement, source)
    if count != 1:
        raise ValueError(f"Notebook must define {name} as a Path exactly once")
    return updated


def _parameter_cell(notebook: dict[str, Any]) -> dict[str, Any]:
    cells = notebook.get("cells")
    if not isinstance(cells, list):
        raise ValueError("Notebook cells are missing")
    matches = [
        cell
        for cell in cells
        if isinstance(cell, dict)
        and "parameters" in cell.get("metadata", {}).get("tags", [])
    ]
    if len(matches) != 1:
        raise ValueError("Notebook must contain exactly one parameters cell")
    return matches[0]


def stage(*, variant: str, source_bundle_sha256: str, output: Path) -> dict[str, Any]:
    if variant not in VARIANTS:
        raise ValueError("Ablation variant must be a or b")
    digest = source_bundle_sha256.strip().lower()
    if not SHA256_PATTERN.fullmatch(digest):
        raise ValueError("Source bundle SHA-256 is invalid")
    if output.exists():
        raise FileExistsError(f"Refusing to overwrite staging directory: {output}")
    output.mkdir(parents=True)
    notebook = json.loads(NOTEBOOK_PATH.read_text(encoding="utf-8"))
    parameters = _parameter_cell(notebook)
    source_value = parameters.get("source")
    if not isinstance(source_value, list) or not all(
        isinstance(line, str) for line in source_value
    ):
        raise ValueError("Notebook parameters cell source is invalid")
    source = "".join(source_value)
    selected = VARIANTS[variant]
    source = _replace_assignment(source, "RUN_MODE", "validation")
    source = _replace_assignment(source, "RUN_ID", str(selected["run_id"]))
    source = _replace_assignment(
        source, "EXPECTED_SOURCE_BUNDLE_SHA256", digest
    )
    source = _replace_path_assignment(
        source, "CONFIG_RELATIVE_PATH", str(selected["config"])
    )
    parameters["source"] = source.splitlines(keepends=True)

    for cell in notebook["cells"]:
        if isinstance(cell, dict) and cell.get("cell_type") == "code":
            cell["execution_count"] = None
            cell["outputs"] = []
    slug = str(selected["slug"])
    code_file = f"{slug}.ipynb"
    (output / code_file).write_text(
        json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    metadata = {
        "id": f"oumarbenlol/{slug}",
        "title": selected["title"],
        "code_file": code_file,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": True,
        "enable_gpu": True,
        "enable_tpu": False,
        "enable_internet": False,
        "keywords": ["organ-on-chip", "image-quality", "ablation"],
        "dataset_sources": list(DATASET_SOURCES),
        "kernel_sources": [],
        "competition_sources": [],
        "model_sources": [],
        "machine_shape": "NvidiaTeslaT4",
    }
    (output / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "variant": variant,
        "kernel": metadata["id"],
        "run_id": selected["run_id"],
        "config": selected["config"],
        "source_bundle_sha256": digest,
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(VARIANTS), required=True)
    parser.add_argument("--source-bundle-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    print(
        json.dumps(
            stage(
                variant=arguments.variant,
                source_bundle_sha256=arguments.source_bundle_sha256,
                output=arguments.output,
            ),
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
