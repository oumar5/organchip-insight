import importlib.metadata
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "backend/scripts" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = load_script("probe_cnn_runtime")
builder = load_script("build_runtime_probe_notebook")


@pytest.fixture
def runtime(monkeypatch):
    contract = json.loads(
        (ROOT / "backend/experiments/ooc-cnn/kaggle-runtime-contract.json").read_text()
    )
    versions = {
        name: entry["locally_validated_version"]
        for name, entry in contract["runtime"]["packages"].items()
    }
    monkeypatch.setattr(probe.platform, "python_version", lambda: "3.12.14")

    def version(name):
        if name not in versions:
            raise importlib.metadata.PackageNotFoundError(name)
        return versions[name]

    monkeypatch.setattr(probe.importlib.metadata, "version", version)
    return contract, versions


def test_probe_accepts_local_contract_versions(runtime):
    contract, versions = runtime
    versions["torch"] += "+cu128"
    assert probe.inspect_versions(contract)["blockers"] == []


def test_probe_reports_unsupported_torch_pair(runtime):
    contract, versions = runtime
    versions["torch"] = "2.11.0"
    result = probe.inspect_versions(contract)
    assert any("torch 2.11.0 violates" in error for error in result["blockers"])
    assert "Torch/torchvision pair is not accepted" in result["blockers"]


def test_probe_records_missing_dependencies_without_crashing(runtime):
    contract, versions = runtime
    del versions["onnxruntime"]
    result = probe.inspect_versions(contract)
    assert result["packages"]["onnxruntime"] is None
    assert "Missing package: onnxruntime" in result["blockers"]


def test_probe_notebook_is_synchronized_and_compiles():
    expected = builder.build_notebook()
    assert json.loads(builder.NOTEBOOK.read_text()) == expected
    for cell in expected["cells"]:
        if cell["cell_type"] == "code":
            assert cell["execution_count"] is None
            assert cell["outputs"] == []
            compile("".join(cell["source"]), cell["id"], "exec")


def test_probe_saves_report_even_when_functional_checks_fail(runtime, monkeypatch, tmp_path):
    contract, _ = runtime
    monkeypatch.setitem(sys.modules, "torch", None)
    report = probe.probe_runtime(contract, tmp_path)
    assert not report["runtime_checks_passed"]
    assert not report["benchmark_eligible"]
    assert not report["checks"]["cuda_mobilenet_forward"]["passed"]
    assert not report["checks"]["cpu_onnx_round_trip"]["passed"]
    saved = list(tmp_path.glob("organchip-runtime-probe-*/runtime-report.json"))
    assert len(saved) == 1
    assert json.loads(saved[0].read_text()) == report
