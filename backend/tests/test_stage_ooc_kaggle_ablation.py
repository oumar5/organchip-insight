import importlib.util
import json

import pytest

ROOT = __file__.rsplit("/backend/tests/", 1)[0]
SPEC = importlib.util.spec_from_file_location(
    "stage_ooc_kaggle_ablation",
    f"{ROOT}/backend/scripts/stage_ooc_kaggle_ablation.py",
)
stage = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stage)


@pytest.mark.parametrize(
    ("variant", "size"),
    (("a", "gray224"), ("b", "gray448")),
)
def test_stage_ablation_is_private_offline_and_excludes_test(
    tmp_path, variant: str, size: str
) -> None:
    output = tmp_path / variant
    result = stage.stage(
        variant=variant,
        source_bundle_sha256="a" * 64,
        output=output,
    )
    metadata = json.loads((output / "kernel-metadata.json").read_text())
    notebook = json.loads((output / metadata["code_file"]).read_text())
    parameters = next(
        cell
        for cell in notebook["cells"]
        if "parameters" in cell.get("metadata", {}).get("tags", [])
    )
    source = "".join(parameters["source"])

    assert metadata["is_private"] is True
    assert metadata["enable_gpu"] is True
    assert metadata["enable_internet"] is False
    assert metadata["dataset_sources"] == list(stage.DATASET_SOURCES)
    assert not any("frozen-test" in item for item in metadata["dataset_sources"])
    assert result["kernel"] == metadata["id"]
    assert size in source
    assert 'RUN_MODE = "validation"' in source
    assert f'RUN_ID = "kaggle-validation-campaign-v2-{size}"' in source
    assert f'EXPECTED_SOURCE_BUNDLE_SHA256 = "{"a" * 64}"' in source
    assert all(
        cell.get("execution_count") is None and cell.get("outputs") == []
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )


def test_stage_ablation_refuses_invalid_inputs_and_overwrite(tmp_path) -> None:
    with pytest.raises(ValueError, match="SHA-256"):
        stage.stage(variant="a", source_bundle_sha256="invalid", output=tmp_path / "a")
    output = tmp_path / "b"
    stage.stage(variant="b", source_bundle_sha256="b" * 64, output=output)
    with pytest.raises(FileExistsError, match="overwrite"):
        stage.stage(variant="b", source_bundle_sha256="b" * 64, output=output)
