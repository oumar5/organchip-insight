"""Run and verify the bounded real-image product smoke test."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = BACKEND_ROOT.parent
sys.path.insert(0, str(BACKEND_ROOT))

from inference import resolve_input_images, run_inference, sha256_file  # noqa: E402

MANIFEST = PROJECT_ROOT / "data/manifests/product-real-smoke-v1.json"


def main() -> None:
    images = resolve_input_images([], [], MANIFEST, recursive=False)
    before = {path: sha256_file(path) for path in images}
    with tempfile.TemporaryDirectory(prefix="organchip-real-smoke-") as temporary:
        output_dir = Path(temporary)
        result_path = run_inference(images, output_dir)
        payload = json.loads(result_path.read_text(encoding="utf-8"))
        if len(payload["image_results"]) != len(images):
            raise SystemExit("Real-image smoke produced an unexpected result count")
        if len(payload["artifacts"]) != len(images):
            raise SystemExit("Real-image smoke produced an unexpected artifact count")
        expected_names = [path.name for path in images]
        actual_names = [row["filename"] for row in payload["image_results"]]
        if actual_names != expected_names:
            raise SystemExit("Real-image smoke result order or filenames changed")
        for artifact in payload["artifacts"]:
            if not (output_dir / artifact["filename"]).is_file():
                raise SystemExit(f"Missing real-image smoke overlay: {artifact['filename']}")

    after = {path: sha256_file(path) for path in images}
    if after != before:
        raise SystemExit("A real-image smoke source changed during inference")
    print(
        json.dumps(
            {
                "status": "passed",
                "manifest": str(MANIFEST.relative_to(PROJECT_ROOT)),
                "image_count": len(images),
                "source_sha256_unchanged": True,
                "warning": "Connected components are not validated cell counts.",
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
