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
SCENE_STARTS_MS = (0, 16_000, 42_000, 72_000, 105_000, 128_000, 156_000)
NARRATION_STARTS_MS = (
    0,
    8_000,
    16_000,
    29_000,
    42_000,
    57_000,
    72_000,
    88_000,
    105_000,
    116_000,
    128_000,
    142_000,
    156_000,
    168_000,
)
NARRATION_CHAPTER_IDS = (
    "promise-a",
    "promise-b",
    "protocol-a",
    "protocol-b",
    "analysis-a",
    "analysis-b",
    "limits-a",
    "limits-b",
    "export-a",
    "export-b",
    "benchmarks-a",
    "benchmarks-b",
    "credibility-a",
    "credibility-b",
)


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
            "Organ-on-chip microscopy needs more than a model score.",
            "OrganChip Insight keeps images, measurements, provenance, and limits together.",
            "Record the objective before analysis and import hash-locked public images.",
            "Uploads stay separate from inference, so sources are never duplicated.",
            "The adaptive engine runs locally on CPU, without model weights.",
            "It analyzes the original TIFF; the normalized preview is display-only.",
            "Zoom source and segmentation together to inspect every overlay.",
            "Components are not cells, and physical units require documented calibration.",
            "JSON and CSV preserve the experiment, engine, and per-image results.",
            "A second completed experiment is compared descriptively, without biological claims.",
            "Versioned benchmarks report accuracy, uncertainty, runtime, and memory.",
            "Promotion rules stay visible, including negative results.",
            "Quality classification did not escape acquisition shortcuts.",
            "The frozen test set remains unopened; the product abstains and shows its limits.",
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
            "La microscopie d'organes sur puce exige plus qu'un score de modèle.",
            "OrganChip Insight réunit images, mesures, provenance et limites scientifiques.",
            "Consignez l'objectif avant l'analyse, puis importez les images publiques vérifiées.",
            "L'import reste séparé de l'inférence ; les sources ne sont jamais dupliquées.",
            "Le moteur adaptatif fonctionne localement sur processeur, sans poids appris.",
            "Il analyse le TIFF original ; l'aperçu normalisé sert uniquement à l'affichage.",
            "Zoomez ensemble sur la source et la segmentation pour inspecter l'overlay.",
            "Les composantes ne sont pas des cellules ; les unités physiques "
            "exigent une calibration.",
            "Les exports JSON et CSV conservent l'expérience et les résultats par image.",
            "Une seconde expérience se compare descriptivement, sans conclusion biologique.",
            "Les benchmarks versionnés publient précision, incertitude, temps et mémoire.",
            "Les règles de promotion restent visibles, y compris les résultats négatifs.",
            "La classification de qualité n'échappe pas aux raccourcis d'acquisition.",
            "Le jeu de test gelé reste fermé ; le produit s'abstient et montre ses limites.",
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

    for index, (chapter_id, start_ms, text) in enumerate(
        zip(
            NARRATION_CHAPTER_IDS,
            NARRATION_STARTS_MS,
            specification.narration,
            strict=True,
        ),
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
            NARRATION_STARTS_MS[index]
            if index < len(NARRATION_STARTS_MS)
            else raw_duration_ms
        )
        if end_ms >= next_start_ms - 250:
            raise RuntimeError(
                f"Narration {specification.language} scene {index} exceeds its window: "
                f"{end_ms} >= {next_start_ms - 250}"
            )
        segments.append(
            {
                "chapterId": chapter_id,
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


def clear_delegated_narration(
    project_root: Path,
    specification: LanguageSpec,
) -> None:
    """Remove generated narration before Demo Studio rebuilds it."""
    run_root = project_root / "public/runs" / specification.journey_id
    shutil.rmtree(run_root / "audio", ignore_errors=True)
    for generated_path in (
        run_root / "narration.json",
        run_root / f"{specification.language}.srt",
    ):
        generated_path.unlink(missing_ok=True)


def create_timeline(
    project_root: Path,
    specification: LanguageSpec,
    raw_duration_ms: int,
    video_asset: str,
) -> None:
    run_root = project_root / "public/runs" / specification.journey_id
    run_root.mkdir(parents=True, exist_ok=True)
    events: list[dict[str, object]] = [
        {
            "type": "chapter",
            "chapterId": chapter_id,
            "chapterTitle": chapter_id,
            "atMs": start_ms,
        }
        for chapter_id, start_ms in zip(
            NARRATION_CHAPTER_IDS,
            NARRATION_STARTS_MS,
            strict=True,
        )
    ]
    for index, (start_ms, caption) in enumerate(
        zip(SCENE_STARTS_MS, specification.captions, strict=True)
    ):
        end_ms = (
            SCENE_STARTS_MS[index + 1]
            if index + 1 < len(SCENE_STARTS_MS)
            else raw_duration_ms
        )
        events.append(
            {
                "type": "action",
                "chapterId": NARRATION_CHAPTER_IDS[index * 2],
                "chapterTitle": caption,
                "action": "pause",
                "atMs": start_ms,
                "endMs": end_ms,
                "caption": caption,
                "focus": False,
            }
        )
    events.sort(key=lambda event: (int(event["atMs"]), event["type"] == "action"))

    timeline = {
        "journeyId": specification.journey_id,
        "title": specification.title,
        "language": specification.language,
        "width": 1280,
        "height": 720,
        "fps": 30,
        "durationMs": raw_duration_ms,
        "video": video_asset,
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
    parser.add_argument(
        "--raw-video",
        type=Path,
        help="Backward-compatible shared capture for both languages.",
    )
    parser.add_argument("--raw-video-en", type=Path)
    parser.add_argument("--raw-video-fr", type=Path)
    parser.add_argument("--project-root", type=Path, default=DEFAULT_PROJECT_ROOT)
    parser.add_argument(
        "--timeline-only",
        action="store_true",
        help="Let Demo Studio generate neural narration and subtitles.",
    )
    arguments = parser.parse_args()

    project_root = arguments.project_root.resolve()
    if arguments.raw_video is not None:
        shared_capture = arguments.raw_video.resolve()
        raw_videos = {language: shared_capture for language in LANGUAGES}
    elif arguments.raw_video_en is not None and arguments.raw_video_fr is not None:
        raw_videos = {
            "en": arguments.raw_video_en.resolve(),
            "fr": arguments.raw_video_fr.resolve(),
        }
    else:
        parser.error("provide --raw-video or both --raw-video-en and --raw-video-fr")

    raw_durations_ms = {language: duration_ms(path) for language, path in raw_videos.items()}
    for language, raw_duration_ms in raw_durations_ms.items():
        if not 170_000 <= raw_duration_ms <= 190_000:
            raise RuntimeError(
                f"Unexpected {language} raw capture duration: {raw_duration_ms} ms"
            )
    if abs(raw_durations_ms["en"] - raw_durations_ms["fr"]) > 1_000:
        raise RuntimeError("English and French captures differ by more than one second")

    shared_root = project_root / "public/runs/shared"
    shared_root.mkdir(parents=True, exist_ok=True)
    video_assets: dict[str, str] = {}
    for language, raw_video in raw_videos.items():
        shared_capture = (shared_root / f"capture-{language}.webm").resolve()
        if raw_video != shared_capture:
            shutil.copy2(raw_video, shared_capture)
        video_assets[language] = f"runs/shared/{shared_capture.name}"

    result: dict[str, object] = {
        "raw_duration_ms": raw_durations_ms,
        "languages": {},
    }
    for language, specification in LANGUAGES.items():
        raw_duration_ms = raw_durations_ms[language]
        create_timeline(
            project_root,
            specification,
            raw_duration_ms,
            video_assets[language],
        )
        if arguments.timeline_only:
            clear_delegated_narration(project_root, specification)
            result["languages"][language] = {
                "journey_id": specification.journey_id,
                "narration": "delegated-to-demo-studio",
            }
        else:
            segments, subtitle_path = create_narration(
                project_root, specification, raw_duration_ms
            )
            result["languages"][language] = {
                "journey_id": specification.journey_id,
                "voice": specification.voice,
                "subtitle": str(subtitle_path),
                "narration_seconds": round(
                    sum(
                        int(segment["endMs"]) - int(segment["startMs"])
                        for segment in segments
                    )
                    / 1000,
                    3,
                ),
            }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
