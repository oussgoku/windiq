#!/usr/bin/env bash
set -euo pipefail

cd /opt/windiq
: "${WINDIQ_IMAGE:?Set WINDIQ_IMAGE to the commit-tagged image}"
: "${GITHUB_ACTOR:?Set GITHUB_ACTOR}"
test -f .env || { echo 'Missing /opt/windiq/.env' >&2; exit 1; }

# The workflow passes its package token on stdin. Keep Docker's auth outside
# the deployment directory and remove it on exit.
export DOCKER_CONFIG
DOCKER_CONFIG="$(mktemp -d)"
trap 'rm -rf "$DOCKER_CONFIG"' EXIT
docker login ghcr.io -u "$GITHUB_ACTOR" --password-stdin

compose=(docker compose --env-file .env -f compose.production.yaml)
"${compose[@]}" pull api scheduler
"${compose[@]}" up -d db
"${compose[@]}" run --rm api alembic upgrade head
"${compose[@]}" up -d api scheduler proxy

# Allow the API a short startup window before reporting a successful release.
for attempt in {1..20}; do
  if "${compose[@]}" exec -T api python -c \
    'import urllib.request; urllib.request.urlopen("http://localhost:8000/ready", timeout=5).read()'; then
    exit 0
  fi
  sleep 3
done
echo 'API readiness failed after 60 seconds' >&2
exit 1
