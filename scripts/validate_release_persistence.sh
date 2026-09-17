#!/bin/sh
set -eu

PROJECT_NAME="organchip-release-validation"
BACKEND_PORT="18282"
FRONTEND_PORT="18283"
REPOSITORY_ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
EXPERIMENT_NAME="Release persistence ${ORGANCHIP_RELEASE_VALIDATION_ID:-local}"

compose() {
  ORGANCHIP_BACKEND_PORT="$BACKEND_PORT" \
    ORGANCHIP_FRONTEND_PORT="$FRONTEND_PORT" \
    docker compose --project-directory "$REPOSITORY_ROOT" -p "$PROJECT_NAME" "$@"
}

cleanup() {
  compose down --volumes --remove-orphans
}

trap cleanup EXIT INT TERM
cleanup
compose up --detach --build --wait

PLAYWRIGHT_BASE_URL="http://127.0.0.1:$FRONTEND_PORT" \
  ORGANCHIP_PERSISTENCE_PHASE="seed" \
  ORGANCHIP_PERSISTENCE_EXPERIMENT_NAME="$EXPERIMENT_NAME" \
  npm --prefix "$REPOSITORY_ROOT/frontend" run test:e2e -- e2e/release-persistence.spec.ts

compose restart
compose up --detach --wait

PLAYWRIGHT_BASE_URL="http://127.0.0.1:$FRONTEND_PORT" \
  ORGANCHIP_PERSISTENCE_PHASE="verify" \
  ORGANCHIP_PERSISTENCE_EXPERIMENT_NAME="$EXPERIMENT_NAME" \
  npm --prefix "$REPOSITORY_ROOT/frontend" run test:e2e -- e2e/release-persistence.spec.ts
