#!/bin/sh
set -eu

PROJECT_NAME="organchip-demo-video"
BACKEND_PORT="18282"
FRONTEND_PORT="18283"
REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
DEMO_STUDIO_ROOT=${DEMO_STUDIO_ROOT:-"$(CDPATH= cd -- "$REPOSITORY_ROOT/.." && pwd)/demo-studio"}
DEMO_STUDIO_CLI="$DEMO_STUDIO_ROOT/dist/cli.js"
DEMO_PROJECT_ROOT="$REPOSITORY_ROOT/demo/video"
DEMO_CONFIG="$DEMO_PROJECT_ROOT/demo.config.yaml"
TEMPORARY_DIRECTORY=$(mktemp -d)
RAW_VIDEO="$TEMPORARY_DIRECTORY/organchip-insight-demo.webm"
MANIFEST="$REPOSITORY_ROOT/data/manifests/product-real-smoke-v1.json"

cleanup() {
  ORGANCHIP_BACKEND_PORT="$BACKEND_PORT" \
    ORGANCHIP_FRONTEND_PORT="$FRONTEND_PORT" \
    docker compose --project-directory "$REPOSITORY_ROOT" \
      -p "$PROJECT_NAME" down --volumes --remove-orphans >/dev/null 2>&1 || true
  rm -rf "$TEMPORARY_DIRECTORY"
}

trap cleanup EXIT INT TERM

for command in docker ffmpeg ffprobe node say; do
  command -v "$command" >/dev/null 2>&1 || {
    echo "Required command is missing: $command" >&2
    exit 1
  }
done

if [ ! -f "$DEMO_STUDIO_CLI" ]; then
  echo "Demo Studio CLI is missing: $DEMO_STUDIO_CLI" >&2
  echo "Set DEMO_STUDIO_ROOT to the local Demo Studio checkout." >&2
  exit 1
fi

mkdir -p "$REPOSITORY_ROOT/output/video"
ORGANCHIP_BACKEND_PORT="$BACKEND_PORT" \
  ORGANCHIP_FRONTEND_PORT="$FRONTEND_PORT" \
  docker compose --project-directory "$REPOSITORY_ROOT" \
    -p "$PROJECT_NAME" up --detach --build --wait

PLAYWRIGHT_BASE_URL="http://127.0.0.1:$FRONTEND_PORT" \
  ORGANCHIP_REAL_E2E_MANIFEST="$MANIFEST" \
  ORGANCHIP_DEMO_RAW_VIDEO="$RAW_VIDEO" \
  ORGANCHIP_DEMO_SUBTITLE="$TEMPORARY_DIRECTORY/raw-capture.en.srt" \
  ORGANCHIP_DEMO_BURN_CAPTIONS="false" \
  node "$REPOSITORY_ROOT/frontend/scripts/record-demo-video.mjs"

uv run --project "$REPOSITORY_ROOT/backend" \
  python "$REPOSITORY_ROOT/backend/scripts/prepare_demo_studio_video.py" \
  --raw-video "$RAW_VIDEO" \
  --project-root "$DEMO_PROJECT_ROOT"

node "$DEMO_STUDIO_CLI" validate --project "$DEMO_CONFIG"

for language in en fr; do
  journey="organchip-insight-demo-$language"
  node "$DEMO_STUDIO_CLI" render \
    --project "$DEMO_CONFIG" \
    --journey "$journey"
  rendered_video="$DEMO_PROJECT_ROOT/output/$journey-$language.mp4"
  final_video="$REPOSITORY_ROOT/output/video/organchip-insight-demo-candidate-$language.mp4"
  ffmpeg -hide_banner -loglevel error -y \
    -i "$rendered_video" \
    -vf "scale=in_range=full:out_range=tv,format=yuv420p" \
    -c:v libx264 -preset medium -crf 21 -pix_fmt yuv420p \
    -color_range tv -c:a copy -movflags +faststart \
    "$final_video"
  cp "$DEMO_PROJECT_ROOT/public/runs/$journey/$language.srt" \
    "$REPOSITORY_ROOT/output/video/organchip-insight-demo-candidate-$language.srt"
done

uv run --project "$REPOSITORY_ROOT/backend" \
  python "$REPOSITORY_ROOT/backend/scripts/check_demo_video.py"
