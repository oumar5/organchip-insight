"""Offline environment diagnostics with synthetic inputs and no trained weights."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def inspect_versions(contract: dict[str, Any]) -> dict[str, Any]:
    runtime = contract["runtime"]
    versions: dict[str, str | None] = {}
    blockers: list[str] = []
    for name in runtime["packages"]:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
            blockers.append(f"Missing package: {name}")
    try:
        from packaging.specifiers import SpecifierSet
        from packaging.version import Version

        python_spec = runtime["python"]["specifier"]
        if Version(platform.python_version()) not in SpecifierSet(python_spec):
            blockers.append(f"Python {platform.python_version()} violates {python_spec}")
        for name, version in versions.items():
            spec = runtime["packages"][name]["specifier"]
            if version is not None and Version(version) not in SpecifierSet(spec):
                blockers.append(f"{name} {version} violates {spec}")
        pair_ok = any(
            all(
                versions[name] is not None
                and Version(versions[name]) in SpecifierSet(f"=={pair[name]}")
                for name in ("torch", "torchvision")
            )
            for pair in runtime["accepted_torch_torchvision_pairs"]
        )
        if not pair_ok:
            blockers.append("Torch/torchvision pair is not accepted")
    except Exception as error:
        blockers.append(f"Version validation failed: {type(error).__name__}: {error}")
    return {"python": platform.python_version(), "packages": versions, "blockers": blockers}


def probe_runtime(contract: dict[str, Any], output_directory: Path) -> dict[str, Any]:
    output_directory.mkdir(parents=True, exist_ok=True)
    run_directory = Path(tempfile.mkdtemp(prefix="organchip-runtime-probe-", dir=output_directory))
    report: dict[str, Any] = {
        "schema_version": 1,
        "scope": "runtime-only; synthetic inputs; random weights; no dataset or training",
        "benchmark_eligible": False,
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "contract_id": contract["contract_id"],
        "contract_semantic_sha256": hashlib.sha256(
            json.dumps(contract, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest(),
        "platform": platform.system(),
        "versions": inspect_versions(contract),
        "checks": {},
    }

    def check(name, operation):
        try:
            report["checks"][name] = {"passed": True, "details": operation()}
        except Exception as error:
            report["checks"][name] = {
                "passed": False,
                "error": f"{type(error).__name__}: {error}",
            }

    def cuda_forward():
        import torch
        from torchvision.models import mobilenet_v3_small

        if not torch.cuda.is_available():
            raise RuntimeError("CUDA unavailable: GPU validation remains blocked")
        torch.manual_seed(20260916)
        model = mobilenet_v3_small(weights=None, num_classes=2).eval().cuda()
        with torch.inference_mode():
            output = model(torch.randn(1, 3, 224, 224, device="cuda"))
        if list(output.shape) != [1, 2] or not torch.isfinite(output).all().item():
            raise RuntimeError("Invalid CUDA output")
        torch.cuda.synchronize()
        return {
            "gpu_names": [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())],
            "torch_cuda": torch.version.cuda,
            "cudnn": torch.backends.cudnn.version(),
            "output_shape": list(output.shape),
        }

    def onnx_round_trip():
        import numpy as np
        import onnx
        import onnxruntime as ort
        import torch
        from torchvision.models import mobilenet_v3_small

        torch.manual_seed(20260916)
        model = mobilenet_v3_small(weights=None, num_classes=2).eval().cpu()
        sample = torch.randn(2, 3, 224, 224)
        model_path = run_directory / "synthetic-model.onnx"
        torch.onnx.export(
            model,
            sample,
            model_path,
            input_names=["images"],
            output_names=["logits"],
            dynamic_axes={"images": {0: "batch"}, "logits": {0: "batch"}},
            opset_version=18,
            do_constant_folding=True,
            dynamo=False,
        )
        onnx.checker.check_model(onnx.load(model_path))
        session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        errors = []
        for batch in (1, 2, 3):
            values = torch.randn(batch, 3, 224, 224)
            with torch.inference_mode():
                expected = model(values).numpy()
            actual = session.run(["logits"], {"images": values.numpy()})[0]
            if not np.isfinite(actual).all() or not np.isfinite(expected).all():
                raise RuntimeError("Non-finite parity output")
            np.testing.assert_allclose(actual, expected, rtol=0, atol=1e-4)
            errors.append(float(np.max(np.abs(actual - expected))))
        return {"batch_sizes": [1, 2, 3], "max_absolute_error": max(errors), "tolerance": 1e-4}

    # Diagnostic checks run even when version bounds fail; they never relax the contract.
    check("cuda_mobilenet_forward", cuda_forward)
    check("cpu_onnx_round_trip", onnx_round_trip)
    report["runtime_checks_passed"] = not report["versions"]["blockers"] and all(
        result["passed"] for result in report["checks"].values()
    )
    report_path = run_directory / "runtime-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    print(f"Report: {report_path}")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    probe_runtime(json.loads(args.contract.read_text(encoding="utf-8")), args.output_directory)


if __name__ == "__main__":
    main()
