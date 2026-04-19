#!/usr/bin/env bash
set -euo pipefail

PORT="${OPENCLAW_PORT:-18789}"
PROVIDER_MODEL="${OPENCLAW_PROVIDER_MODEL:-google/gemini-3-flash-preview}"

if ! command -v openclaw >/dev/null 2>&1; then
  echo "openclaw CLI is not installed or not on PATH." >&2
  echo "Install Node.js 20+ first, then run: npm install -g openclaw@latest" >&2
  exit 127
fi

openclaw config set gateway.mode local
openclaw config set gateway.bind loopback
openclaw config set gateway.port "$PORT"
openclaw config set gateway.http.endpoints.chatCompletions.enabled true
openclaw config set agents.defaults.model.primary "$PROVIDER_MODEL" || true

if [[ -n "${GEMINI_API_KEY:-}" ]]; then
  openclaw config set env.vars.GEMINI_API_KEY "$GEMINI_API_KEY"
  openclaw config set env.vars.GOOGLE_API_KEY "$GEMINI_API_KEY" || true
fi

if [[ -n "${OPENAI_API_KEY:-}" ]]; then
  openclaw config set env.vars.OPENAI_API_KEY "$OPENAI_API_KEY"
fi

if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  openclaw config set env.vars.ANTHROPIC_API_KEY "$ANTHROPIC_API_KEY"
fi

echo "OpenClaw config file:"
openclaw config file
echo
echo "Configured OpenClaw gateway on 127.0.0.1:${PORT}"
echo "Provider model: ${PROVIDER_MODEL}"
