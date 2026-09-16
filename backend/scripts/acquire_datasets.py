"""Download, verify, and safely extract resources declared in the data manifest."""

import argparse
import json
from pathlib import Path

from app.datasets import (
    DatasetError,
    download_resource,
    extract_resource,
    load_manifest,
    selected_resources,
    verify_resource,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest", type=Path, default=PROJECT_ROOT / "data/manifests/datasets.json"
    )
    parser.add_argument("--resource", action="append", dest="resources")
    parser.add_argument("--verify-only", action="store_true")
    parser.add_argument("--no-extract", action="store_true")
    parser.add_argument(
        "--allow-large",
        action="store_true",
        help="Required for resources marked large, even when explicitly selected",
    )
    args = parser.parse_args()

    try:
        manifest = load_manifest(args.manifest.resolve())
        resources = selected_resources(manifest, args.resources)
        results = []
        for resource in resources:
            if resource.get("large") and not args.allow_large:
                raise DatasetError(
                    f"Resource {resource['id']} is marked large; pass --allow-large explicitly"
                )
            path = PROJECT_ROOT / resource["path"]
            if not path.exists():
                if args.verify_only:
                    raise DatasetError(f"Missing resource {resource['id']}: {path}")
                print(f"Downloading {resource['id']} -> {resource['path']}")
                download_resource(resource, PROJECT_ROOT)
            results.append(verify_resource(resource, PROJECT_ROOT))
            if resource.get("extraction") and not args.no_extract:
                results.append(extract_resource(resource, PROJECT_ROOT))
    except DatasetError as error:
        raise SystemExit(str(error)) from error

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
