#!/usr/bin/env python3
"""Fail-closed static checks for the offline OoC CNN Kaggle notebook."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_NOTEBOOK = PROJECT_ROOT / "notebooks/ooc-cnn-kaggle.ipynb"
REQUIRED_TAGS = (
    "parameters",
    "workspace-staging",
    "preflight",
    "smoke",
    "validation",
    "reporting",
    "export",
    "freeze",
    "archive",
    "final-eval",
)
FORBIDDEN_FRAGMENTS = (
    "%pip",
    "!pip",
    "pip install",
    "conda install",
    "mamba install",
    "micromamba install",
    "apt-get",
    "!wget",
    "!curl",
    "urllib.request",
    "urlretrieve(",
    "requests.get(",
    "httpx.get(",
    "torch.hub",
    "load_state_dict_from_url",
    "weights=default",
    "weights=\"default\"",
    "weights='default'",
    "kaggle.api",
    "kagglehub",
    "competitions.submit",
    "dataset_create",
    "dataset_version",
    "kernels.push",
    "os.system(",
    "shell=true",
    "os.symlink(",
    ".symlink_to(",
)


def _cell_source(cell: dict[str, Any]) -> str:
    source = cell.get("source")
    if isinstance(source, str):
        return source
    if isinstance(source, list) and all(isinstance(line, str) for line in source):
        return "".join(source)
    raise ValueError("Every notebook cell must contain textual source")


def _require(source: str, fragments: tuple[str, ...], label: str) -> None:
    missing = [fragment for fragment in fragments if fragment not in source]
    if missing:
        raise ValueError(f"{label} is missing invariants: {', '.join(missing)}")


def _load_notebook(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Notebook is not valid JSON: {path}") from error
    if not isinstance(value, dict):
        raise ValueError("Notebook root must be a JSON object")
    return value


def check_notebook(path: Path) -> None:
    notebook = _load_notebook(path)
    if notebook.get("nbformat") != 4 or notebook.get("nbformat_minor", -1) < 5:
        raise ValueError("Notebook must use nbformat 4.5 or newer")
    cells = notebook.get("cells")
    if not isinstance(cells, list) or not cells:
        raise ValueError("Notebook must contain cells")

    identifiers: set[str] = set()
    tagged_cells: dict[str, str] = {}
    code_sources: list[str] = []
    all_sources: list[str] = []
    for index, cell_value in enumerate(cells):
        if not isinstance(cell_value, dict):
            raise ValueError(f"Cell {index} must be an object")
        cell = cell_value
        identifier = cell.get("id")
        if (
            not isinstance(identifier, str)
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", identifier)
            or identifier in identifiers
        ):
            raise ValueError(f"Cell {index} has a missing, invalid, or duplicate id")
        identifiers.add(identifier)
        source = _cell_source(cell)
        all_sources.append(source)
        cell_type = cell.get("cell_type")
        if cell_type == "code":
            if cell.get("execution_count") is not None or cell.get("outputs") != []:
                raise ValueError(f"Code cell {identifier} must be clean and unexecuted")
            try:
                compile(source, f"{path.name}#{identifier}", "exec")
            except SyntaxError as error:
                raise ValueError(f"Code cell {identifier} is not valid Python") from error
            code_sources.append(source)
        elif cell_type != "markdown":
            raise ValueError(f"Unsupported cell type in {identifier}: {cell_type}")

        metadata = cell.get("metadata", {})
        if not isinstance(metadata, dict):
            raise ValueError(f"Cell {identifier} metadata must be an object")
        tags = metadata.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise ValueError(f"Cell {identifier} tags must be strings")
        for tag in tags:
            if tag in REQUIRED_TAGS:
                if tag in tagged_cells:
                    raise ValueError(f"Notebook contains duplicate {tag} cells")
                tagged_cells[tag] = source

    missing_tags = sorted(set(REQUIRED_TAGS) - set(tagged_cells))
    if missing_tags:
        raise ValueError(f"Notebook is missing tagged cells: {', '.join(missing_tags)}")

    code = "\n".join(code_sources)
    all_text = "\n".join(all_sources)
    lowered = all_text.casefold()
    forbidden = [fragment for fragment in FORBIDDEN_FRAGMENTS if fragment in lowered]
    if forbidden:
        raise ValueError(f"Notebook contains forbidden operations: {', '.join(forbidden)}")

    parameters = tagged_cells["parameters"]
    _require(
        parameters,
        (
            'RUN_MODE = "validation"',
            'RESUME_VALIDATION_FROM = ""',
            "ENABLE_FINAL_EVAL = False",
            'FINAL_EVAL_CONFIRMATION = ""',
            'EXPECTED_FINAL_EVAL_CONFIRMATION = "OPEN_FROZEN_TEST_ONCE"',
            'FINAL_EVAL_REASON = ""',
            "def mounted_dataset_path(slug: str, relative: str) -> Path:",
            'Path("/kaggle/input") / slug',
            'Path("/kaggle/input/datasets/oumarbenlol") / slug',
            "for prefix in (Path(), Path(slug))",
            'SOURCE_DATASET_SLUG = "organchip-insight-source-campaign-v2"',
            'SOURCE_INPUT_DIR = mounted_dataset_path(SOURCE_DATASET_SLUG, "organchip-insight")',
            "SOURCE_MANIFEST_PATH = mounted_dataset_path("
            'SOURCE_DATASET_SLUG, "source-bundle-manifest.json")',
            "EXPECTED_SOURCE_BUNDLE_SHA256",
            "TRAIN_VALIDATION_IMAGE_ROOT = mounted_dataset_path("
            '"organchip-train-validation-v2", "train-validation/images")',
            "WEIGHTS_INPUT_DIR = mounted_dataset_path("
            '"organchip-cnn-offline-resources-v1", "resources")',
            "OFFLINE_ONNXRUNTIME_WHEEL_NAME",
            "OFFLINE_ONNXRUNTIME_WHEEL_SHA256",
            'OFFLINE_SITE_PACKAGES = WORKSPACE_ROOT / "offline-site-packages"',
            'FINAL_IMAGE_ROOT = Path("/kaggle/input/datasets/oumarbenlol/',
            'FROZEN_TEST_DATASET_ROOT = Path("/kaggle/input/datasets/oumarbenlol/'
            'organchip-frozen-test-v2-zip")',
            'WORKSPACE_ROOT = Path("/kaggle/working/',
            'CONFIG_RELATIVE_PATH = Path("backend/training/configs/',
            'TRAIN_VALIDATION_MANIFEST_RELATIVE = Path("data/splits/',
            "ooc-campaign-v2-train-validation.csv",
            'TEST_MANIFEST_RELATIVE = Path("data/splits/ooc-campaign-v2-test.csv")',
            'EXPECTED_SPLIT_ID = "ooc-grouped-by-temporal-campaign-v2"',
            "INITIAL_WEIGHTS_SHA256",
            "FROZEN_MANIFEST_SHA256",
        ),
        "parameters cell",
    )
    config_match = re.search(
        r'CONFIG_RELATIVE_PATH = Path\("(backend/training/configs/'
        r'ooc-cnn-mobilenet-v3-small-campaign-v2(?:-gray(?:224|448))?\.json)"\)',
        parameters,
    )
    if config_match is None:
        raise ValueError("parameters cell contains an unauthorized CNN config path")

    staging = tagged_cells["workspace-staging"]
    _require(
        staging,
        (
            "shutil.copytree(SOURCE_INPUT_DIR, PROJECT_ROOT",
            "source_ignore",
            '"raw"',
            '"ooc-campaign-v2-test.csv"',
            '"ooc-campaign-v2.csv"',
            "SOURCE_BUNDLE_SHA256 = sha256_tree(SOURCE_INPUT_DIR)",
            "SOURCE_BUNDLE_SHA256 != validate_sha256(EXPECTED_SOURCE_BUNDLE_SHA256",
            "SOURCE_MANIFEST_PATH.is_file()",
            'SOURCE_MANIFEST.get("source_tree_sha256") != SOURCE_BUNDLE_SHA256',
            'SOURCE_GIT_COMMIT = SOURCE_MANIFEST.get("source_commit")',
            "path.is_symlink()",
            "RESUME_REQUESTED = bool(RESUME_VALIDATION_FROM.strip())",
            'if RESUME_REQUESTED and RUN_MODE != "validation"',
            "Source persistée différente du bundle autorisé",
            "Définir RESUME_VALIDATION_FROM pour une reprise vérifiée",
            "def bootstrap_offline_wheel(",
            "checked_input_file(source_root, wheel_name)",
            "sha256_file(wheel) != expected_sha256",
            "stat.S_ISLNK(member_mode)",
            "archive.extractall(target)",
            "sys.path.insert(0, str(target))",
            'importlib.metadata.version("onnxruntime")',
            "ONNXRUNTIME_BOOTSTRAP = bootstrap_offline_wheel(",
            "python_paths = [backend_path, str(OFFLINE_SITE_PACKAGES)]",
            'environment["PYTHONPATH"] = os.pathsep.join(python_paths)',
            "check=False",
            "stdout=subprocess.PIPE",
            "completed.check_returncode()",
            "reuse_existing=RESUME_REQUESTED",
        ),
        "workspace-staging cell",
    )
    if "choisir un nouveau RUN_ID" in staging:
        raise ValueError("RUN_ID cannot resolve an existing PROJECT_ROOT")
    if code.count("shutil.copytree(") != 1:
        raise ValueError("Exactly one copytree is allowed, for the small source bundle only")
    if "dirs_exist_ok=True" in code:
        raise ValueError("Implicit whole-tree merges are forbidden")
    if any(
        fragment in code
        for fragment in ("copy_manifest_images", "DATASET_INPUT_ROOT", "final_images_source")
    ):
        raise ValueError("Image copying is forbidden; use the read-only --image-root")

    preflight = tagged_cells["preflight"]
    _require(
        preflight,
        (
            "load_experiment_config",
            "load_split_lock",
            "SPLIT_LOCK.split_id != EXPECTED_SPLIT_ID",
            "SPLIT_LOCK.source_sha256 != EXPECTED_SPLIT_SOURCE_SHA256",
            'RUN_MODE != "final-eval" and FROZEN_TEST_DATASET_ROOT.exists()',
            "validate_runtime_contract",
            "validate_required_hashes",
            "torch.cuda.is_available()",
            "torch.cuda.get_device_name(0)",
            'RUN_MODE in {"validation", "final-eval"}',
            'ACTIVE_IMAGE_ROOT.resolve().relative_to(Path("/kaggle/input").resolve())',
            '"source_bundle_sha256": SOURCE_BUNDLE_SHA256',
            '"config_sha256": CONFIG.sha256',
            '"runtime_contract_sha256"',
            '"split_lock_sha256"',
            '"canonical_grouped_split_sha256": SPLIT_LOCK.source_sha256',
            '"train_validation_manifest_sha256"',
            '"dataset_inventory_sha256"',
            "COMMON_REQUIRED_HASHES",
            "VALIDATED_REQUIRED_HASHES",
            "provided_hashes=PROVIDED_REQUIRED_HASHES",
            "load_initial_weights",
        ),
        "preflight cell",
    )
    if "REPLACE_WITH_" in code:
        raise ValueError("Notebook contains unresolved hash placeholders")

    smoke = tagged_cells["smoke"]
    _require(
        smoke,
        (
            'if RUN_MODE == "smoke"',
            '"train"',
            '"--mode", "smoke"',
            '"--image-root", str(TRAIN_VALIDATION_IMAGE_ROOT)',
        ),
        "smoke cell",
    )
    if "--weights" in smoke or "test" in smoke.casefold():
        raise ValueError("Smoke cell must not receive weights or test inputs")

    validation = tagged_cells["validation"]
    _require(
        validation,
        (
            'if RUN_MODE == "validation"',
            '"train"',
            '"--mode", "validation"',
            '"--device", "cuda"',
            '"--image-root", str(TRAIN_VALIDATION_IMAGE_ROOT)',
            '"--weights", str(INITIAL_WEIGHTS_PATH)',
            '"--weights-sha256", INITIAL_WEIGHTS_SHA256',
            '"--weights-metadata", str(INITIAL_WEIGHTS_METADATA_PATH)',
            "if RESUME_VALIDATION_FROM",
            "checked_input_file(PROJECT_ROOT, RESUME_VALIDATION_FROM)",
            'validation_arguments.extend(["--resume-from", str(resume_checkpoint)])',
        ),
        "validation cell",
    )
    if "--test-manifest" in validation or "FINAL_IMAGE_ROOT" in validation:
        raise ValueError("Validation cell must not receive final/test inputs")

    reporting = tagged_cells["reporting"]
    _require(
        reporting,
        (
            "test_manifest_opened",
            'for artifact_name in ("learning_curves", "confusion_matrix")',
            "sha256_file(artifact_path)",
            "display(Image(",
        ),
        "reporting cell",
    )

    export = tagged_cells["export"]
    _require(
        export,
        (
            '"export"',
            '"--checkpoint-sha256"',
            '"--selection-report-sha256"',
            '"--output-directory"',
            '"export-report.json"',
            'export_report["export"]',
        ),
        "export cell",
    )

    freeze = tagged_cells["freeze"]
    _require(
        freeze,
        (
            'RUN_MODE == "validation"',
            '"freeze"',
            '"--validation-report"',
            '"--checkpoint"',
            '"--output"',
        ),
        "freeze cell",
    )

    archive = tagged_cells["archive"]
    _require(
        archive,
        (
            'if RUN_MODE == "validation"',
            '"archive"',
            '"--run-directory"',
            '"--output"',
            '"--source-bundle-sha256", SOURCE_BUNDLE_SHA256',
            '"--source-commit", SOURCE_GIT_COMMIT',
            'Path("/kaggle/working")',
            'f"{RUN_ID}-artifacts.zip"',
            "sha256_file(archive_path)",
            "FileLink(str(archive_path))",
        ),
        "archive cell",
    )
    if "/kaggle/input" in archive or "TRAIN_VALIDATION_IMAGE_ROOT" in archive:
        raise ValueError("Artifact archive must never include Kaggle input images")

    final = tagged_cells["final-eval"]
    _require(
        final,
        (
            'if RUN_MODE == "final-eval"',
            "if ENABLE_FINAL_EVAL is not True",
            "if FINAL_EVAL_CONFIRMATION != EXPECTED_FINAL_EVAL_CONFIRMATION",
            "if not FINAL_EVAL_REASON.strip()",
            'FINAL_IMAGE_ROOT.resolve().relative_to(Path("/kaggle/input").resolve())',
            '"final-eval"',
            '"--device", "cuda"',
            '"--image-root", str(FINAL_IMAGE_ROOT)',
            '"--test-manifest"',
            '"--test-manifest-root", str(FINAL_BUNDLE_ROOT)',
            '"--frozen-manifest-sha256"',
            '"--confirm-test-open", FINAL_EVAL_CONFIRMATION',
            '"--reason", FINAL_EVAL_REASON',
            'if artifact_name != "test_manifest"',
            "external_test_manifest = FINAL_BUNDLE_ROOT / TEST_MANIFEST_RELATIVE",
            "FINAL_REQUIRED_HASHES = validate_required_hashes",
            '"frozen_manifest_sha256"',
            '"checkpoint_sha256"',
            '"test_manifest_sha256"',
            'receipt_relative = Path(final_report["protocol"]["test_access_receipt"])',
            'receipt_directory = final_run_directory / "test-access"',
            "shutil.copy2(receipt_source, receipt_copy)",
            'final_archive_path = Path("/kaggle/working") / f"{RUN_ID}-artifacts.zip"',
            '"--source-bundle-sha256", SOURCE_BUNDLE_SHA256',
            '"--source-commit", SOURCE_GIT_COMMIT',
            "FileLink(str(final_archive_path))",
        ),
        "final-eval cell",
    )
    if "shutil.copytree(" in final:
        raise ValueError("Final evaluation must use --image-root, not copy the image tree")
    if 'str(PROJECT_ROOT / TEST_MANIFEST_RELATIVE)' in final:
        raise ValueError("Final evaluation must not stage or pre-open the test manifest")
    guard_positions = (
        final.index("if ENABLE_FINAL_EVAL is not True"),
        final.index("if FINAL_EVAL_CONFIRMATION != EXPECTED_FINAL_EVAL_CONFIRMATION"),
        final.index("if not FINAL_EVAL_REASON.strip()"),
    )
    command_position = final.index("FINAL_RESULT = run_cli([")
    if max(guard_positions) >= command_position:
        raise ValueError("Final evaluation command must appear after every explicit guard")
    if final.index("FINAL_REQUIRED_HASHES = validate_required_hashes") >= command_position:
        raise ValueError("Final required hashes must be validated before test access")

    non_final = "\n".join(source for tag, source in tagged_cells.items() if tag != "final-eval")
    if "--test-manifest" in non_final:
        raise ValueError("Only the final-eval cell may pass a test manifest")
    if code.count('"--image-root"') < 3:
        raise ValueError("Smoke, validation, and final-eval must all pass --image-root")
    if "reports/test-access/ooc-cnn" not in all_text:
        raise ValueError("Notebook must require preserving the workspace test receipt")


def main() -> int:
    notebook_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_NOTEBOOK
    if len(sys.argv) > 2:
        raise SystemExit("usage: check_ooc_cnn_notebook.py [notebook.ipynb]")
    check_notebook(notebook_path)
    print(f"OK: {notebook_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
