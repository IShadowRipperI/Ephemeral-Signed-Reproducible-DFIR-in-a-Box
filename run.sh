#!/usr/bin/env bash
set -Eeuo pipefail

# Config via env or defaults
IMAGE="${IMAGE:-dfirbox:0.1}"
PROFILE="${1:-/app/profiles/windows-triage.yml}"
EVIDENCE="${EVIDENCE:-$PWD/evidence}"
OUT="${OUT:-$PWD/out}"

# Platform:
# - keep linux/amd64 for your current image
# - set PLATFORM="" to omit the flag
# - set PLATFORM="linux/arm64" if you build a native arm64 image
PLATFORM="${PLATFORM:-linux/amd64}"

mkdir -p "$EVIDENCE" "$OUT"

# Build docker args
DOCKER_ARGS=(--rm)
[[ -n "$PLATFORM" ]] && DOCKER_ARGS+=(--platform "$PLATFORM")
DOCKER_ARGS+=(-v "$EVIDENCE:/evidence:ro" -v "$OUT:/out")

exec docker run "${DOCKER_ARGS[@]}" \
  "$IMAGE" dfirbox run -e /evidence -o /out -p "$PROFILE"
