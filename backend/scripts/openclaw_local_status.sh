#!/usr/bin/env bash
set -euo pipefail

if [ -f ".env" ]; then
  set -a
  # shellcheck disable=SC1091
  source ".env"
  set +a
fi

PORT="${OPENCLAW_PORT:-18789}"
CHAT_MODEL="${OPENCLAW_CHAT_MODEL:-openclaw}"
PROVIDER_MODEL="${OPENCLAW_PROVIDER_MODEL:-${OPENCLAW_MODEL:-google/gemini-3-flash-preview}}"

echo "OpenClaw CLI:"
openclaw --version || true
echo
echo "Provider model: $PROVIDER_MODEL"
echo "HTTP chat model: $CHAT_MODEL"
echo

echo "Gateway status:"
openclaw gateway status || true
echo

echo "HTTP root:"
curl -s -o /dev/null -w 'http://127.0.0.1:'"$PORT"'/ -> %{http_code}\n' "http://127.0.0.1:${PORT}/" || true
echo

echo "Chat completions test:"
curl -sS "http://127.0.0.1:${PORT}/v1/chat/completions" \
  -H 'Content-Type: application/json' \
  -d '{"model":"'"$CHAT_MODEL"'","messages":[{"role":"user","content":"Reply with exactly: openclaw-ok"}]}' || true
echo
