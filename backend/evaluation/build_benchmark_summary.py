"""Generate the product benchmark view from versioned scientific reports."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "frontend/public/benchmark-summary.json"
REPORT_PATHS = {
    "bbbc019_adaptive": PROJECT_ROOT
    / "reports/benchmarks/bbbc019-microfluidic-adaptive-v1.json",
    "bbbc019_micro_sam": PROJECT_ROOT
    / "reports/benchmarks/bbbc019-microfluidic-microsam-vit-b-lm-apg.json",
    "bbbc038_micro_sam": PROJECT_ROOT
    / "reports/benchmarks/bbbc038-stage1-subset-v1-microsam-vit-b-lm-apg.json",
    "iorganoassay_adaptive": PROJECT_ROOT
    / "reports/benchmarks/iorganoassay-validation-v1.1.0-adaptive-v1.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metric(
    label: str,
    value: float,
    *,
    format_name: str = "decimal",
    interval: list[float] | None = None,
) -> dict[str, Any]:
    output: dict[str, Any] = {
        "label": label,
        "value": value,
        "format": format_name,
    }
    if interval is not None:
        output["interval_95_percent"] = interval
    return output


def build_summary(
    reports: dict[str, dict[str, Any]],
    sources: list[dict[str, Any]],
) -> dict[str, Any]:
    adaptive = reports["bbbc019_adaptive"]
    micro_sam_foreground = reports["bbbc019_micro_sam"]
    micro_sam_instances = reports["bbbc038_micro_sam"]
    iorganoassay_adaptive = reports["iorganoassay_adaptive"]
    if adaptive["benchmark_id"] != "bbbc019-microfluidic-adaptive-segmentation-v1":
        raise ValueError("Unexpected adaptive BBBC019 report")
    if (
        micro_sam_foreground["benchmark_id"]
        != "bbbc019-microfluidic-micro-sam-vit-b-lm-apg"
    ):
        raise ValueError("Unexpected µSAM BBBC019 report")
    if (
        micro_sam_instances["benchmark_id"]
        != "bbbc038-stage1-subset-v1-micro-sam-vit-b-lm-apg"
    ):
        raise ValueError("Unexpected µSAM BBBC038 report")
    if (
        iorganoassay_adaptive["benchmark_id"]
        != "iorganoassay-validation-v1.1.0-adaptive-v1"
    ):
        raise ValueError("Unexpected iOrganoAssay report")
    if adaptive["results"]["image_count"] != micro_sam_foreground["results"][
        "image_count"
    ]:
        raise ValueError("BBBC019 reports do not cover the same number of images")

    return {
        "schema_version": 1,
        "generated_from": sources,
        "sections": [
            {
                "id": "bbbc019-foreground",
                "title": "Premier plan microfluidique · BBBC019",
                "scope": (
                    "13 images DIC externes avec masques binaires manuels. Comparaison "
                    "à protocole identique ; ce jeu n'est pas le dataset OoC du concours."
                ),
                "rows": [
                    {
                        "engine": "Segmentation adaptative v1",
                        "status": "Moteur produit",
                        "metrics": [
                            _metric(
                                "Macro-F1",
                                adaptive["results"]["macro"]["f1"],
                                interval=adaptive["results"][
                                    "macro_bootstrap_95_percent"
                                ]["f1"],
                            ),
                            _metric("Macro-IoU", adaptive["results"]["macro"]["iou"]),
                            _metric(
                                "Temps / image",
                                adaptive["performance"][
                                    "mean_inference_seconds_per_image"
                                ],
                                format_name="seconds",
                            ),
                            _metric(
                                "Mémoire max.",
                                adaptive["performance"]["process_max_rss_mb"],
                                format_name="megabytes",
                            ),
                        ],
                    },
                    {
                        "engine": "µSAM vit_b_lm · APG",
                        "status": "Benchmark isolé",
                        "metrics": [
                            _metric(
                                "Macro-F1",
                                micro_sam_foreground["results"]["macro"]["f1"],
                                interval=micro_sam_foreground["results"][
                                    "macro_bootstrap_95_percent"
                                ]["f1"],
                            ),
                            _metric(
                                "Macro-IoU",
                                micro_sam_foreground["results"]["macro"]["iou"],
                            ),
                            _metric(
                                "Temps / image",
                                micro_sam_foreground["performance"][
                                    "mean_inference_seconds_per_image"
                                ],
                                format_name="seconds",
                            ),
                            _metric(
                                "Mémoire max.",
                                micro_sam_foreground["performance"][
                                    "process_max_rss_mb"
                                ],
                                format_name="megabytes",
                            ),
                        ],
                    },
                ],
                "decision": (
                    "µSAM améliore le premier plan sur ce petit jeu externe, mais son "
                    "coût CPU et le benchmark d'instances BBBC038 empêchent sa promotion."
                ),
            },
            {
                "id": "bbbc038-instances",
                "title": "Instances nucléaires · BBBC038",
                "scope": (
                    "Audit zéro-shot pré-enregistré sur 12 images choisies pour leur "
                    "diversité, pas une estimation de population sur les 670 images."
                ),
                "rows": [
                    {
                        "engine": "µSAM vit_b_lm · APG",
                        "status": "Non promu · 2 critères sur 3 échouent",
                        "metrics": [
                            _metric(
                                "Macro-F1 objet · IoU 0,50",
                                micro_sam_instances["results"]["objects"]["0.5"][
                                    "macro"
                                ]["f1"],
                                interval=micro_sam_instances["results"]["objects"][
                                    "0.5"
                                ]["macro_bootstrap_95_percent"]["f1"],
                            ),
                            _metric(
                                "Macro-F1 objet · IoU 0,75",
                                micro_sam_instances["results"]["objects"]["0.75"][
                                    "macro"
                                ]["f1"],
                                interval=micro_sam_instances["results"]["objects"][
                                    "0.75"
                                ]["macro_bootstrap_95_percent"]["f1"],
                            ),
                            _metric(
                                "Erreur comptage médiane",
                                micro_sam_instances["results"]["count"][
                                    "median_absolute_percentage_error"
                                ],
                                format_name="percent",
                            ),
                            _metric(
                                "Temps / image",
                                micro_sam_instances["performance"][
                                    "mean_inference_seconds_per_image"
                                ],
                                format_name="seconds",
                            ),
                            _metric(
                                "Mémoire max.",
                                micro_sam_instances["performance"][
                                    "process_max_rss_mb"
                                ],
                                format_name="megabytes",
                            ),
                        ],
                    }
                ],
                "decision": (
                    "Ce résultat nucléaire externe ne valide pas le comptage de "
                    "cellules sur les images OoC."
                ),
            },
            {
                "id": "iorganoassay-organoid-foreground",
                "title": "Premier plan d'organoïde · iOrganoAssay v1.1.0",
                "scope": (
                    "Validation externe pré-enregistrée sur les 28 triplets officiels "
                    "BF/GT/Seg (14 contrôle, 14 DSS). Le masque cible un organoïde, "
                    "pas toutes les instances du champ."
                ),
                "rows": [
                    {
                        "engine": "Segmentation adaptative v1",
                        "status": "Preuve externe · 3 critères sur 3 atteints",
                        "metrics": [
                            _metric(
                                "Macro-F1",
                                iorganoassay_adaptive["results"]["adaptive_macro"][
                                    "f1"
                                ],
                                interval=iorganoassay_adaptive["results"][
                                    "adaptive_macro_f1_bootstrap_95_percent"
                                ],
                            ),
                            _metric(
                                "Macro-IoU",
                                iorganoassay_adaptive["results"]["adaptive_macro"][
                                    "iou"
                                ],
                            ),
                            _metric(
                                "F1 contrôle",
                                iorganoassay_adaptive["results"][
                                    "adaptive_macro_by_condition"
                                ]["Ctrl"]["f1"],
                            ),
                            _metric(
                                "F1 DSS",
                                iorganoassay_adaptive["results"][
                                    "adaptive_macro_by_condition"
                                ]["DSS"]["f1"],
                            ),
                            _metric(
                                "Temps / image",
                                iorganoassay_adaptive["performance"][
                                    "mean_adaptive_inference_seconds_per_image"
                                ],
                                format_name="seconds",
                            ),
                        ],
                    }
                ],
                "decision": (
                    "Le résultat peut être présenté comme une preuve externe de "
                    "segmentation d'organoïde. Il ne valide ni la segmentation OoC, "
                    "ni une classification good/bad, ni un comptage cellulaire."
                ),
            },
        ],
    }


def generate_summary() -> dict[str, Any]:
    reports = {
        name: json.loads(path.read_text(encoding="utf-8"))
        for name, path in REPORT_PATHS.items()
    }
    sources = [
        {
            "path": str(path.relative_to(PROJECT_ROOT)),
            "sha256": sha256_file(path),
        }
        for path in REPORT_PATHS.values()
    ]
    return build_summary(reports, sources)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    serialized = json.dumps(generate_summary(), indent=2, ensure_ascii=False) + "\n"
    if arguments.check:
        if not arguments.output.is_file() or arguments.output.read_text(
            encoding="utf-8"
        ) != serialized:
            raise SystemExit("Frontend benchmark summary is not synchronized")
        print(f"OK: {arguments.output}")
        return
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(serialized, encoding="utf-8")
    print(f"Wrote {arguments.output}")


if __name__ == "__main__":
    main()
