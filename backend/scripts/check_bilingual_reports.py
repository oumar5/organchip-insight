"""Check structural parity and release hygiene of the bilingual report sources."""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    "en": REPOSITORY_ROOT / "docs/04-submission/technical-report-en.md",
    "fr": REPOSITORY_ROOT / "docs/04-submission/technical-report-fr.md",
}
NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+)*)\.\s")
PLACEHOLDER = re.compile(
    r"\b(?:TODO|TBD|TO COMPLETE|À COMPLÉTER|A COMPLETER)\b", re.IGNORECASE
)


def structure(path: Path) -> list[tuple[int, str]]:
    entries: list[tuple[int, str]] = []
    unnumbered = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        match = re.match(r"^(##|###)\s+(.+)$", line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        numbered = NUMBERED_HEADING.match(title)
        if numbered:
            key = numbered.group(1)
        else:
            unnumbered += 1
            key = f"unnumbered-{unnumbered}"
        entries.append((level, key))
    return entries


def main() -> None:
    texts = {language: path.read_text(encoding="utf-8") for language, path in SOURCES.items()}
    for language, text in texts.items():
        if "Ben Lol OUMAR" not in text:
            raise SystemExit(f"Missing canonical author identity in {language} report")
        placeholder = PLACEHOLDER.search(text)
        if placeholder:
            raise SystemExit(
                f"Unresolved placeholder in {language} report: {placeholder.group(0)}"
            )
    structures = {language: structure(path) for language, path in SOURCES.items()}
    if structures["en"] != structures["fr"]:
        raise SystemExit(
            "Bilingual report heading structures differ:\n"
            f"EN={structures['en']}\nFR={structures['fr']}"
        )
    if len(structures["en"]) < 20:
        raise SystemExit("Technical report structure is unexpectedly incomplete")
    print(
        "OK: bilingual report sources have matching structures "
        f"({len(structures['en'])} sections/subsections), canonical identity, "
        "and no unresolved placeholders."
    )


if __name__ == "__main__":
    main()
