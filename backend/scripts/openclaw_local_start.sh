#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

PORT="${OPENCLAW_PORT:-18789}"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw CLI is not installed or not on PATH." >&2
  exit 1
fi

echo "Starting OpenClaw gateway on 127.0.0.1:${PORT}..."
exec openclaw gateway run --auth none --bind loopback --port "$PORT"
