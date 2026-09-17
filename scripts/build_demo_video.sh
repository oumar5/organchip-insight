#!/bin/sh
set -eu

PROJECT_NAME="organchip-demo-video"
BACKEND_PORT="18282"
FRONTEND_PORT="18283"
REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
TEMPORARY_DIRECTORY=$(mktemp -d)
RAW_VIDEO="$TEMPORARY_DIRECTORY/organchip-insight-demo.webm"
OUTPUT_VIDEO="$REPOSITORY_ROOT/output/video/organchip-insight-demo-candidate.mp4"
MANIFEST="$REPOSITORY_ROOT/data/manifests/product-real-smoke-v1.json"

cleanup() {
  ORGANCHIP_BACKEND_PORT="$BACKEND_PORT" \
    ORGANCHIP_FRONTEND_PORT="$FRONTEND_PORT" \
    docker compose --project-directory "$REPOSITORY_ROOT" \
      -p "$PROJECT_NAME" down --volumes --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$TEMPORARY_DIRECTORY"
}

trap cleanup EXIT INT TERM

for command in docker ffmpeg ffprobe node; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Required command is missing: $command" >&2
    exit 1
  }
done

mkdir -p "$REPOSITORY_ROOT/output/video"
ORGANCHIP_BACKEND_PORT="$BACKEND_PORT" \
  ORGANCHIP_FRONTEND_PORT="$FRONTEND_PORT" \
  docker compose --project-directory "$REPOSITORY_ROOT" \
    -p "$PROJECT_NAME" up --detach --build --wait

PLAYWRIGHT_BASE_URL="http://127.0.0.1:$FRONTEND_PORT" \
  ORGANCHIP_REAL_E2E_MANIFEST="$MANIFEST" \
  ORGANCHIP_DEMO_RAW_VIDEO="$RAW_VIDEO" \
  node "$REPOSITORY_ROOT/frontend/scripts/record-demo-video.mjs"

ffmpeg -hide_banner -loglevel error -y \
  -i "$RAW_VIDEO" \
  -f lavfi -i "anullsrc=channel_layout=stereo:sample_rate=48000" \
  -map 0:v:0 -map 1:a:0 -shortest \
  -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p \
  -c:a aac -b:a 128k -movflags +faststart \
  -metadata title="OrganChip Insight demo candidate" \
  -metadata comment="Captioned, silent-audio competition demo candidate" \
  "$OUTPUT_VIDEO"

uv run --project "$REPOSITORY_ROOT/backend" \
  python "$REPOSITORY_ROOT/backend/scripts/check_demo_video.py"
