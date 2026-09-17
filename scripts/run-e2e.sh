#!/bin/sh
set -eu

PROJECT_NAME="organchip-e2e"
BACKEND_PORT="18182"
FRONTEND_PORT="18183"
REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

cleanup() {
  ORGANCHIP_BACKEND_PORT="$BACKEND_PORT" \
    ORGANCHIP_FRONTEND_PORT="$FRONTEND_PORT" \
    docker compose --project-directory "$REPOSITORY_ROOT" \
      -p "$PROJECT_NAME" down --volumes --remove-orphans
}

trap cleanup EXIT INT TERM

if [ "${ORGANCHIP_E2E_SKIP_BUILD:-0}" = "1" ]; then
  ORGANCHIP_BACKEND_PORT="$BACKEND_PORT" \
    ORGANCHIP_FRONTEND_PORT="$FRONTEND_PORT" \
    docker compose --project-directory "$REPOSITORY_ROOT" \
      -p "$PROJECT_NAME" up --detach --no-build --wait
else
  ORGANCHIP_BACKEND_PORT="$BACKEND_PORT" \
    ORGANCHIP_FRONTEND_PORT="$FRONTEND_PORT" \
    docker compose --project-directory "$REPOSITORY_ROOT" \
      -p "$PROJECT_NAME" up --detach --build --wait
fi

PLAYWRIGHT_BASE_URL="http://127.0.0.1:$FRONTEND_PORT" \
  npm --prefix "$REPOSITORY_ROOT/frontend" run test:e2e
