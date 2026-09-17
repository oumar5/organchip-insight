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
NATURAL_VOICE_ROOT=${ORGANCHIP_NATURAL_VOICE_ROOT:-"$(CDPATH= cd -- "$REPOSITORY_ROOT/.." && pwd)/solmik/product-demos/.runtime"}
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

for command in docker ffmpeg ffprobe node; do
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

CHATTERBOX_PYTHON=${CHATTERBOX_PYTHON:-"$NATURAL_VOICE_ROOT/env-chatterbox/bin/python"}
RHUBARB_COMMAND=${RHUBARB_COMMAND:-"$NATURAL_VOICE_ROOT/rhubarb/Rhubarb-Lip-Sync-1.14.0-macOS/rhubarb"}
HF_HOME=${HF_HOME:-"$NATURAL_VOICE_ROOT/cache/huggingface"}
TORCH_HOME=${TORCH_HOME:-"$NATURAL_VOICE_ROOT/cache/torch"}
NLTK_DATA=${NLTK_DATA:-"$NATURAL_VOICE_ROOT/cache/nltk_data"}
NUMBA_CACHE_DIR="$TEMPORARY_DIRECTORY/numba-cache"
CHATTERBOX_DEVICE=${CHATTERBOX_DEVICE:-cpu}
CHATTERBOX_EXAGGERATION=${CHATTERBOX_EXAGGERATION:-0.55}
CHATTERBOX_CFG_WEIGHT=${CHATTERBOX_CFG_WEIGHT:-0.4}
HF_HUB_OFFLINE=${HF_HUB_OFFLINE:-1}
TRANSFORMERS_OFFLINE=${TRANSFORMERS_OFFLINE:-1}
export CHATTERBOX_PYTHON RHUBARB_COMMAND HF_HOME TORCH_HOME NLTK_DATA
export NUMBA_CACHE_DIR CHATTERBOX_DEVICE CHATTERBOX_EXAGGERATION CHATTERBOX_CFG_WEIGHT
export HF_HUB_OFFLINE TRANSFORMERS_OFFLINE
mkdir -p "$NUMBA_CACHE_DIR"

if [ ! -x "$CHATTERBOX_PYTHON" ] || [ ! -x "$RHUBARB_COMMAND" ]; then
  echo "Natural voice runtimes are missing under: $NATURAL_VOICE_ROOT" >&2
  echo "Set ORGANCHIP_NATURAL_VOICE_ROOT to a compatible local runtime." >&2
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
  --project-root "$DEMO_PROJECT_ROOT" \
  --timeline-only

node "$DEMO_STUDIO_CLI" validate --project "$DEMO_CONFIG"

for language in en fr; do
  journey="organchip-insight-demo-$language"
  node "$DEMO_STUDIO_CLI" narrate \
    --project "$DEMO_CONFIG" \
    --journey "$journey" \
    --provider chatterbox
  node "$DEMO_STUDIO_CLI" avatar \
    --project "$DEMO_CONFIG" \
    --journey "$journey" \
    --provider rhubarb
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
