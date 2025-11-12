#!/usr/bin/env bash
set -euo pipefail

# Simple wrapper to expose CLI as "dfirbox"
if [[ "${1:-}" == "dfirbox" ]]; then
  shift
  exec python3 -m src.cli "$@"
fi

exec "$@"
