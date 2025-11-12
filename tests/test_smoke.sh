#!/usr/bin/env bash
set -euo pipefail
mkdir -p evidence out
echo "cmd.exe /c whoami" > evidence/demo.txt
docker run --rm \
  --user 1000:1000 \
  -v "$PWD/evidence":/evidence:ro \
  -v "$PWD/out":/out \
  dfirbox:0.1 dfirbox run -e /evidence -o /out -p /app/profiles/windows-triage.yml
echo "Report generated at out/dfirbox_report.html"
