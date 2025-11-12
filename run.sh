#!/usr/bin/env bash
set -euo pipefail
IMAGE="${IMAGE:-ghcr.io/<youruser>/dfirbox:0.1}"
PROFILE="${1:-/app/profiles/windows-triage.yml}"
mkdir -p evidence out
docker run --rm ${PLATFORM:+--platform "$PLATFORM"} \
  -v "$PWD/evidence":/evidence:ro -v "$PWD/out":/out \
  "$IMAGE" dfirbox run -e /evidence -o /out -p "$PROFILE"
