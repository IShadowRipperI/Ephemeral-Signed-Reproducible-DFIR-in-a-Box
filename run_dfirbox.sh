#!/usr/bin/env bash
set -euo pipefail

OUTDIR="$PWD/all_output_$(date +%Y-%m-%d_%H-%M-%S)"

docker run --rm \
  --platform linux/amd64 \
  -v "$PWD/evidence:/evidence" \
  -v "$OUTDIR:/out" \
  dfirbox:test \
  dfirbox run \
    -e /evidence \
    -o /out \
    -p /app/profiles/windows-triage.yml

echo "Output in: $OUTDIR"
