#!/usr/bin/env python3
"""Validate the bilingual competition videos without decoding private data."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = REPOSITORY_ROOT / "output/video"
MAX_BYTES = 100 * 1024 * 1024
LANGUAGES = {
    "en": {
        "phrase": "frozen test set remains unopened",
        "video": OUTPUT_ROOT / "organchip-insight-demo-candidate-en.mp4",
        "subtitle": OUTPUT_ROOT / "organchip-insight-demo-candidate-en.srt",
    },
    "fr": {
        "phrase": "jeu de test gelé reste fermé",
        "video": OUTPUT_ROOT / "organchip-insight-demo-candidate-fr.mp4",
        "subtitle": OUTPUT_ROOT / "organchip-insight-demo-candidate-fr.srt",
    },
}


def fail(message: str) -> None:
    raise SystemExit(message)


def probe_video(path: Path) -> dict[str, object]:
    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def mean_volume(path: Path) -> float:
    completed = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-vn",
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", completed.stderr)
    if not match:
        fail(f"Could not measure demo audio volume: {path.name}")
    return float(match.group(1))


def validate_language(language: str, definition: dict[str, object]) -> dict[str, object]:
    video_path = Path(definition["video"])
    subtitle_path = Path(definition["subtitle"])
    required_phrase = str(definition["phrase"])
    if not video_path.is_file():
        fail(f"{language.upper()} demo video is missing; run `make demo-video`.")
    if not subtitle_path.is_file():
        fail(f"{language.upper()} subtitle sidecar is missing; run `make demo-video`.")
    if video_path.stat().st_size > MAX_BYTES:
        fail(f"{language.upper()} demo video exceeds GitHub's 100 MB per-file limit.")

    probe = probe_video(video_path)
    streams = probe.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(video_streams) != 1 or len(audio_streams) != 1:
        fail(f"{language.upper()} demo must have one video and one audio stream.")
    video = video_streams[0]
    audio = audio_streams[0]
    duration = float(probe["format"]["duration"])
    if not 90 <= duration <= 300:
        fail(
            f"{language.upper()} demo duration must be between 90 and 300 seconds, "
            f"got {duration:.3f}."
        )
    if (video.get("width"), video.get("height")) != (1280, 720):
        fail(f"{language.upper()} demo must be 1280x720.")
    if video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
        fail(f"{language.upper()} demo must use H.264 yuv420p.")
    if audio.get("codec_name") != "aac":
        fail(f"{language.upper()} demo audio must use AAC.")

    measured_volume = mean_volume(video_path)
    if measured_volume < -45:
        fail(
            f"{language.upper()} demo audio is effectively silent "
            f"({measured_volume:.1f} dB mean)."
        )

    subtitles = subtitle_path.read_text(encoding="utf-8")
    if len(re.findall(r"(?m)^\d+$", subtitles)) != 7:
        fail(f"{language.upper()} subtitles must contain the seven scenes.")
    if re.search(r"(?:/Users|/home)/[^/]+/|[A-Za-z]:\\Users\\", subtitles):
        fail(f"Personal absolute path found in {language.upper()} subtitles.")
    if required_phrase not in subtitles:
        fail(f"{language.upper()} subtitles do not preserve the frozen-test reservation.")

    return {
        "duration_seconds": round(duration, 3),
        "resolution": "1280x720",
        "video_codec": video["codec_name"],
        "audio_codec": audio["codec_name"],
        "mean_volume_db": measured_volume,
        "bytes": video_path.stat().st_size,
        "subtitle_scenes": 7,
    }


def main() -> None:
    results = {
        language: validate_language(language, definition)
        for language, definition in LANGUAGES.items()
    }
    print(json.dumps({"status": "passed", "languages": results}, ensure_ascii=False))


if __name__ == "__main__":
    main()
