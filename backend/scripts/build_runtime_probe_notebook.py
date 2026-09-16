"""Build the standalone diagnostic notebook from versioned local sources."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "notebooks/ooc-runtime-probe-kaggle.ipynb"


def build_notebook() -> dict:
    script = ROOT / "backend/scripts/probe_cnn_runtime.py"
    contract = ROOT / "backend/experiments/ooc-cnn/kaggle-runtime-contract.json"
    source = script.read_text(encoding="utf-8").split('\nif __name__ == "__main__":')[0]
    return {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python"},
            "organchip_sources": {
                "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
                "contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
            },
        },
        "cells": [
            {
                "cell_type": "markdown",
                "id": "instructions",
                "metadata": {},
                "source": [
                    "# OrganChip Insight — runtime probe only\n",
                    "Enable a GPU, disable Internet, attach **no datasets or weights**. ",
                    "Run all cells.\n",
                    "This notebook reports versions and checks MobileNetV3/CUDA and ONNX parity ",
                    "using random weights and synthetic tensors. ",
                    "It does not train or access data.\n",
                    "Download the generated `runtime-report.json`. A failed check is diagnostic; ",
                    "it does not alter dependencies or relax the training runtime contract.\n",
                    "Passing these checks is not scientific validation ",
                    "or a complete training preflight.\n",
                    "Version 2 additionally verifies and extracts the attached ONNX Runtime wheel ",
                    "without pip, network access, or mutation of the Kaggle base environment.\n",
                ],
            },
            {
                "cell_type": "code",
                "id": "diagnostics",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": source.splitlines(keepends=True),
            },
            {
                "cell_type": "code",
                "id": "run-probe",
                "metadata": {},
                "execution_count": None,
                "outputs": [],
                "source": [
                    f"CONTRACT = json.loads({contract.read_text(encoding='utf-8')!r})\n",
                    "OFFLINE_WHEEL = Path('/kaggle/input/datasets/oumarbenlol/"
                    "organchip-cnn-offline-resources-v1/resources/"
                    "onnxruntime-1.22.1-cp312-cp312-manylinux_2_27_x86_64."
                    "manylinux_2_28_x86_64.whl')\n",
                    "OFFLINE_WHEEL_SHA256 = "
                    "'2d39a530aff1ec8d02e365f35e503193991417788641b184f5b1e8c9a6d5ce8d'\n",
                    "OUTPUT_ROOT = Path('/kaggle/working') if Path('/kaggle/working').is_dir() "
                    "else Path.cwd()\n",
                    "runtime_report = probe_runtime(\n",
                    "    CONTRACT, OUTPUT_ROOT, offline_wheel=OFFLINE_WHEEL,\n",
                    "    offline_wheel_sha256=OFFLINE_WHEEL_SHA256,\n",
                    ")\n",
                ],
            },
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = json.dumps(build_notebook(), indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if NOTEBOOK.read_text(encoding="utf-8") != expected:
            raise SystemExit("Runtime probe notebook differs from versioned sources")
        print("OK: runtime probe notebook is synchronized")
    else:
        NOTEBOOK.write_text(expected, encoding="utf-8")
        print(NOTEBOOK)


if __name__ == "__main__":
    main()
