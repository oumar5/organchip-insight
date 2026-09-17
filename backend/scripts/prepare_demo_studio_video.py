#!/usr/bin/env python3
"""Prepare bilingual local narration and Demo Studio render manifests."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PROJECT_ROOT = REPOSITORY_ROOT / "demo/video"
SCENE_STARTS_MS = (0, 18_000, 50_000, 86_000, 116_000, 136_000, 172_000)


@dataclass(frozen=True)
class LanguageSpec:
    language: str
    journey_id: str
    title: str
    voice: str
    rate: int
    captions: tuple[str, ...]
    narration: tuple[str, ...]


LANGUAGES = {
    "en": LanguageSpec(
        language="en",
        journey_id="organchip-insight-demo-en",
        title="OrganChip Insight — evidence-gated microscopy",
        voice="Daniel",
        rate=170,
        captions=(
            "One auditable experiment",
            "A protocol before analysis",
            "Local and source-faithful analysis",
            "Measurements with explicit limits",
            "Reproducible exports",
            "Accuracy and cost together",
            "Honest abstention",
        ),
        narration=(
            "Organ-on-chip microscopy needs more than a model score. OrganChip Insight "
            "keeps images, measurements, provenance, and scientific limits inside one "
            "local experiment.",
            "Before analysis, the user records an objective and imports hash-locked public "
            "microscopy images. Upload is separated from inference, so a failed analysis "
            "never duplicates the source files.",
            "The default adaptive engine runs locally on the CPU without model weights. "
            "The original TIFF is analyzed, while the normalized preview is used only for "
            "inspection.",
            "Each segmentation overlay remains linked to its source and measurements. "
            "Components are never presented as validated cells, and geometry stays in "
            "pixels when physical calibration is unavailable.",
            "JSON and CSV exports preserve the experiment, engine, parameters, per-image "
            "results, and generation time, making every result independently auditable.",
            "Versioned external benchmarks report both accuracy and computational cost. "
            "MicroSAM performs better on BBBC019 foreground segmentation, but it fails two "
            "of three preregistered BBBC038 promotion criteria.",
            "Quality classification did not establish a robust signal independent of "
            "acquisition shortcuts. The frozen test set remains unopened, and the product "
            "ships with abstention, checksums, tests, and explicit limits.",
        ),
    ),
    "fr": LanguageSpec(
        language="fr",
        journey_id="organchip-insight-demo-fr",
        title="OrganChip Insight — microscopie fondée sur les preuves",
        voice="Thomas",
        rate=160,
        captions=(
            "Une expérience auditable",
            "Un protocole avant l'analyse",
            "Une analyse locale fidèle à la source",
            "Des mesures aux limites explicites",
            "Des exports reproductibles",
            "Précision et coût ensemble",
            "Une abstention honnête",
        ),
        narration=(
            "La microscopie d'organes sur puce exige plus qu'un score de modèle. OrganChip "
            "Insight réunit images, mesures, provenance et limites scientifiques dans une "
            "expérience locale.",
            "Avant l'analyse, l'utilisateur consigne un objectif et importe des images "
            "publiques verrouillées par empreinte. L'import reste séparé de l'inférence, "
            "afin qu'un échec d'analyse ne duplique jamais les sources.",
            "Le moteur adaptatif par défaut s'exécute localement sur processeur, sans poids "
            "de modèle. Le TIFF original est analysé ; l'aperçu normalisé sert uniquement "
            "à l'inspection.",
            "Chaque overlay de segmentation reste relié à sa source et à ses mesures. Les "
            "composantes ne sont jamais présentées comme des cellules validées, et la "
            "géométrie reste en pixels sans calibration physique.",
            "Les exports JSON et CSV conservent l'expérience, le moteur, les paramètres, "
            "les résultats par image et l'heure de génération, afin que chaque résultat "
            "soit auditable.",
            "Les benchmarks externes versionnés publient à la fois la précision et le coût "
            "de calcul. MicroSAM est meilleur sur la segmentation BBBC019, mais échoue à "
            "deux des trois critères préenregistrés sur BBBC038.",
            "La classification de qualité n'a pas établi de signal robuste indépendant des "
            "raccourcis d'acquisition. Le jeu de test gelé reste fermé, et le produit livre "
            "abstention, checksums, tests et limites explicites.",
        ),
    ),
}


def run(command: list[str]) -> str:
    completed = subprocess.run(command, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def duration_ms(path: Path) -> int:
    value = run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    return math.ceil(float(value) * 1000)


def srt_time(milliseconds: int) -> str:
    hours, remainder = divmod(max(0, milliseconds), 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"


def create_narration(
    project_root: Path,
    specification: LanguageSpec,
    raw_duration_ms: int,
) -> tuple[list[dict[str, object]], Path]:
    run_root = project_root / "public/runs" / specification.journey_id
    audio_root = run_root / "audio"
    audio_root.mkdir(parents=True, exist_ok=True)
    segments: list[dict[str, object]] = []

    for index, (start_ms, text) in enumerate(
        zip(SCENE_STARTS_MS, specification.narration, strict=True),
        start=1,
    ):
        stem = f"{index:02d}-scene"
        intermediate = audio_root / f"{stem}.aiff"
        output = audio_root / f"{stem}.wav"
        subprocess.run(
            [
                "say",
                "-v",
                specification.voice,
                "-r",
                str(specification.rate),
                "-o",
                str(intermediate),
                text,
            ],
            check=True,
        )
        subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                str(intermediate),
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar",
                "48000",
                "-ac",
                "1",
                "-c:a",
                "pcm_s16le",
                str(output),
            ],
            check=True,
        )
        intermediate.unlink()
        end_ms = start_ms + duration_ms(output)
        next_start_ms = (
            SCENE_STARTS_MS[index] if index < len(SCENE_STARTS_MS) else raw_duration_ms
        )
        if end_ms >= next_start_ms - 250:
            raise RuntimeError(
                f"Narration {specification.language} scene {index} exceeds its window: "
                f"{end_ms} >= {next_start_ms - 250}"
            )
        segments.append(
            {
                "chapterId": (
                    "promise",
                    "protocol",
                    "analysis",
                    "limits",
                    "export",
                    "benchmarks",
                    "credibility",
                )[index - 1],
                "startMs": start_ms,
                "endMs": end_ms,
                "text": text,
                "audio": (
                    f"runs/{specification.journey_id}/audio/{output.name}"
                ),
            }
        )

    narration_manifest = {
        "provider": "none",
        "avatarProvider": "none",
        "language": specification.language,
        "segments": segments,
    }
    (run_root / "narration.json").write_text(
        json.dumps(narration_manifest, ensure_ascii=False, indent=2) + "\n"
    )
    subtitle_path = run_root / f"{specification.language}.srt"
    subtitle_path.write_text(
        "\n".join(
            f"{index}\n{srt_time(int(segment['startMs']))} --> "
            f"{srt_time(int(segment['endMs']))}\n{segment['text']}\n"
            for index, segment in enumerate(segments, start=1)
        ),
        encoding="utf-8",
    )
    return segments, subtitle_path


def create_timeline(
    project_root: Path,
    specification: LanguageSpec,
    raw_duration_ms: int,
) -> None:
    run_root = project_root / "public/runs" / specification.journey_id
    events: list[dict[str, object]] = []
    chapter_ids = (
        "promise",
        "protocol",
        "analysis",
        "limits",
        "export",
        "benchmarks",
        "credibility",
    )
    for index, (chapter_id, start_ms, caption) in enumerate(
        zip(chapter_ids, SCENE_STARTS_MS, specification.captions, strict=True)
    ):
        end_ms = (
            SCENE_STARTS_MS[index + 1]
            if index + 1 < len(SCENE_STARTS_MS)
            else raw_duration_ms
        )
        events.extend(
            [
                {
                    "type": "chapter",
                    "chapterId": chapter_id,
                    "chapterTitle": caption,
                    "atMs": start_ms,
                },
                {
                    "type": "action",
                    "chapterId": chapter_id,
                    "chapterTitle": caption,
                    "action": "pause",
                    "atMs": start_ms,
                    "endMs": end_ms,
                    "caption": caption,
                    "focus": False,
                },
            ]
        )

    timeline = {
        "journeyId": specification.journey_id,
        "title": specification.title,
        "language": specification.language,
        "width": 1280,
        "height": 720,
        "fps": 30,
        "durationMs": raw_duration_ms,
        "video": "runs/shared/capture.webm",
        "presenter": {
            "name": "OrganChip Insight guide",
            "initials": "OCI",
            "asset": "presenters/conseiller-demo-studio.png",
            "mouthAssets": {
                "small": "presenters/conseiller-demo-studio-mouth-small.png",
                "round": "presenters/conseiller-demo-studio-mouth-round.png",
                "wide": "presenters/conseiller-demo-studio-mouth-wide.png",
            },
            "placement": "bottom-left",
            "visibility": "narration",
        },
        "soundtrack": {
            "asset": "music/summer-motivational-corporate.mp3",
            "gainDb": -29,
            "duckingDb": -12,
            "fadeInMs": 1800,
            "fadeOutMs": 2600,
            "loop": True,
            "license": (
                "Summer Motivational Corporate - 30 sec edit, Abydos_Music — "
                "Pixabay Content License."
            ),
        },
        "theme": {
            "background": "#071d17",
            "accent": "#1f7a61",
            "text": "#ffffff",
            "overlay": "rgba(5, 25, 20, 0.91)",
            "logoText": "OrganChip Insight",
        },
        "events": events,
    }
    (run_root / "timeline.json").write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2) + "\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-video", type=Path, required=True)
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    arguments = parser.parse_args()

    raw_video = arguments.raw_video.resolve()
    project_root = arguments.project_root.resolve()
    raw_duration_ms = duration_ms(raw_video)
    if not 190_000 <= raw_duration_ms <= 210_000:
        raise RuntimeError(f"Unexpected raw capture duration: {raw_duration_ms} ms")

    shared_root = project_root / "public/runs/shared"
    shared_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(raw_video, shared_root / "capture.webm")

    result: dict[str, object] = {"raw_duration_ms": raw_duration_ms, "languages": {}}
    for language, specification in LANGUAGES.items():
        segments, subtitle_path = create_narration(
            project_root, specification, raw_duration_ms
        )
        create_timeline(project_root, specification, raw_duration_ms)
        result["languages"][language] = {
            "journey_id": specification.journey_id,
            "voice": specification.voice,
            "subtitle": str(subtitle_path),
            "narration_seconds": round(
                sum(int(segment["endMs"]) - int(segment["startMs"]) for segment in segments)
                / 1000,
                3,
            ),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
