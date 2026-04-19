#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

PORT="${OPENCLAW_PORT:-18789}"
PROVIDER_MODEL="${OPENCLAW_PROVIDER_MODEL:-${OPENCLAW_MODEL:-google/gemini-3-flash-preview}}"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw CLI is not installed or not on PATH." >&2
  exit 1
fi

echo "Configuring OpenClaw local gateway..."
openclaw config set gateway.mode local
openclaw config set gateway.bind loopback
openclaw config set gateway.port "$PORT"
openclaw config set gateway.http.endpoints.chatCompletions.enabled true
openclaw config set agents.defaults.model.primary "$PROVIDER_MODEL" || true

if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  openclaw config set env.vars.ANTHROPIC_API_KEY "$ANTHROPIC_API_KEY"
fi

if [ -n "${OPENAI_API_KEY:-}" ]; then
  openclaw config set env.vars.OPENAI_API_KEY "$OPENAI_API_KEY"
fi

if [ -n "${GEMINI_API_KEY:-}" ]; then
  openclaw config set env.vars.GEMINI_API_KEY "$GEMINI_API_KEY"
fi

if [ -n "${GOOGLE_API_KEY:-}" ]; then
  openclaw config set env.vars.GOOGLE_API_KEY "$GOOGLE_API_KEY"
fi

echo "Config file:"
openclaw config file
echo
echo "Provider model: $PROVIDER_MODEL"
echo "HTTP chat model for /v1/chat/completions: ${OPENCLAW_CHAT_MODEL:-openclaw}"
echo
echo "Done. Start with:"
echo "  scripts/openclaw_local_start.sh"
