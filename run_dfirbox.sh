#!/usr/bin/env bash
set -euo pipefail

OUTDIR="$PWD/out_memproc"

docker buildx build --platform linux/amd64 -t dfirbox:1 .

docker run --rm \
  --platform linux/amd64 \
  -v "$PWD/evidence:/evidence" \
  -v "$OUTDIR:/out" \
  dfirbox:1 \
  dfirbox run \
    -e /evidence \
    -o /out \
    -p /app/profiles/windows-triage.yml

echo "Output in: $OUTDIR"
