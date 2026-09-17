#!/usr/bin/env python3
"""Validate the local competition demo candidate without decoding private data."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VIDEO_PATH = REPOSITORY_ROOT / "output/video/organchip-insight-demo-candidate.mp4"
SUBTITLE_PATH = REPOSITORY_ROOT / "output/video/organchip-insight-demo-candidate.en.srt"
MAX_BYTES = 100 * 1024 * 1024


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if not VIDEO_PATH.is_file():
        fail("Demo video is missing; run `make demo-video`.")
    if not SUBTITLE_PATH.is_file():
        fail("English subtitle sidecar is missing; run `make demo-video`.")
    if VIDEO_PATH.stat().st_size > MAX_BYTES:
        fail("Demo video exceeds GitHub's 100 MB per-file limit.")

    completed = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-of",
            "json",
            str(VIDEO_PATH),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    probe = json.loads(completed.stdout)
    streams = probe.get("streams", [])
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]
    if len(video_streams) != 1 or len(audio_streams) != 1:
        fail("Demo video must contain exactly one video stream and one audio stream.")
    video = video_streams[0]
    audio = audio_streams[0]
    duration = float(probe["format"]["duration"])
    if not 90 <= duration <= 300:
        fail(f"Demo duration must be between 90 and 300 seconds, got {duration:.3f}.")
    if (video.get("width"), video.get("height")) != (1280, 720):
        fail("Demo video must be 1280x720.")
    if video.get("codec_name") != "h264" or video.get("pix_fmt") != "yuv420p":
        fail("Demo video must use H.264 yuv420p for broad browser compatibility.")
    if audio.get("codec_name") != "aac":
        fail("Demo audio stream must use AAC.")

    subtitles = SUBTITLE_PATH.read_text()
    if len(re.findall(r"(?m)^\d+$", subtitles)) != 7:
        fail("Demo subtitle sidecar must contain the seven preregistered scenes.")
    if re.search(r"(?:/Users|/home)/[^/]+/|[A-Za-z]:\\Users\\", subtitles):
        fail("Personal absolute path found in demo subtitles.")
    if "frozen test set remains unopened" not in subtitles:
        fail("Demo subtitles must preserve the frozen-test scientific reservation.")

    print(
        json.dumps(
            {
                "status": "passed",
                "duration_seconds": round(duration, 3),
                "resolution": "1280x720",
                "video_codec": video["codec_name"],
                "audio_codec": audio["codec_name"],
                "bytes": VIDEO_PATH.stat().st_size,
                "subtitle_scenes": 7,
            }
        )
    )


if __name__ == "__main__":
    main()
