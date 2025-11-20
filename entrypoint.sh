#!/usr/bin/env bash
set -euo pipefail

# Simple wrapper to expose CLI as "dfirbox"
if [[ "${1:-}" == "dfirbox" ]]; then
  shift
  # Use the venv python (PATH is set in Dockerfile so "python" is /opt/venv/bin/python)
  exec python -m src.cli "$@"
fi

exec "$@"
