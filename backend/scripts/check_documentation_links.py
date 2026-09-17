"""Validate local Markdown links and reject references to the former docs layout."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MARKDOWN_LINK = re.compile(r"!?\[[^]]*]\(([^)]+)\)")
LEGACY_REFERENCES = (
    "docs/submission/",
    "docs/release/",
    "docs/retours-experience/",
    "docs/product-brief.md",
    "docs/architecture.md",
    "docs/inference.md",
    "docs/data-strategy.md",
    "docs/validation.md",
    "docs/roadmap.md",
)


def markdown_files() -> list[Path]:
    completed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z", "--", "*.md"],
        cwd=REPOSITORY_ROOT,
        check=True,
        capture_output=True,
    )
    candidates = (
        REPOSITORY_ROOT / item.decode()
        for item in completed.stdout.split(b"\0")
        if item
    )
    # `git ls-files -co` still reports tracked paths deleted by a pending
    # rename. Validate the working tree that will be committed, including its
    # untracked destinations, rather than trying to open vanished sources.
    return sorted(path for path in candidates if path.is_file())


def main() -> None:
    failures: list[str] = []
    files = markdown_files()
    for path in files:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(REPOSITORY_ROOT)
        for legacy in LEGACY_REFERENCES:
            if legacy in text:
                failures.append(f"{relative}: legacy documentation path: {legacy}")
        for match in MARKDOWN_LINK.finditer(text):
            raw_target = match.group(1).strip()
            if raw_target.startswith("<") and raw_target.endswith(">"):
                raw_target = raw_target[1:-1]
            target = raw_target.split(maxsplit=1)[0]
            if target.startswith(("http://", "https://", "mailto:", "#", "data:")):
                continue
            path_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not path_part:
                continue
            destination = (path.parent / path_part).resolve()
            try:
                destination.relative_to(REPOSITORY_ROOT)
            except ValueError:
                failures.append(f"{relative}: link escapes the repository: {target}")
                continue
            if not destination.exists():
                failures.append(f"{relative}: missing local link target: {target}")
    if failures:
        raise SystemExit("Documentation link check failed:\n- " + "\n- ".join(failures))
    print(f"OK: {len(files)} Markdown files, local links resolved, no legacy paths.")


if __name__ == "__main__":
    main()
