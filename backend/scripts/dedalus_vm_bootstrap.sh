#!/usr/bin/env bash
set -euo pipefail

# Bootstrap script intended to run inside a fresh Dedalus Machine.
# The control-plane backend provisions the machine; this script installs the
# per-user HIVE runtime stack that will own that user's OpenClaw, MemPalace,
# Telegram workers, and pulse worker.

APP_DIR="${HIVE_REMOTE_APP_DIR:-/opt/hive-brain}"
REPO_URL="${HIVE_REPO_URL:-}"
BACKEND_SUBDIR="${HIVE_BACKEND_SUBDIR:-Hive_mind/backend}"

if [ -z "$REPO_URL" ]; then
  echo "Set HIVE_REPO_URL before running this bootstrap script." >&2
  exit 1
fi

export DEBIAN_FRONTEND=noninteractive

apt-get update
apt-get install -y curl git python3 python3-venv python3-pip ca-certificates

if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
  apt-get install -y nodejs
fi

mkdir -p "$APP_DIR"
if [ ! -d "$APP_DIR/.git" ]; then
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi

cd "$APP_DIR/$BACKEND_SUBDIR"
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if ! command -v openclaw >/dev/null 2>&1; then
  npm install -g openclaw
fi

mkdir -p data

cat > .env <<EOF
HIVE_STATE_PATH=data/hive_state.json
HIVE_RUNTIME_MODE=dedalus_worker
HIVE_MEMPALACE_ENABLED=true
HIVE_MEMPALACE_PATH=data/mempalace
HIVE_MEMPALACE_AGENT=hive_brain
OPENCLAW_URL=http://127.0.0.1:18789/v1/chat/completions
OPENCLAW_HEALTH_URL=http://127.0.0.1:18789/
OPENCLAW_CHAT_MODEL=openclaw
OPENCLAW_PROVIDER_MODEL=${OPENCLAW_PROVIDER_MODEL:-google/gemini-3-flash-preview}
GEMINI_API_KEY=${GEMINI_API_KEY:-}
EOF

cat > /etc/systemd/system/hive-backend.service <<EOF
[Unit]
Description=HIVE Brain user runtime backend
After=network.target

[Service]
WorkingDirectory=$APP_DIR/$BACKEND_SUBDIR
EnvironmentFile=$APP_DIR/$BACKEND_SUBDIR/.env
ExecStart=$APP_DIR/$BACKEND_SUBDIR/.venv/bin/uvicorn main:app --host 127.0.0.1 --port 8010
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hive-backend.service
systemctl restart hive-backend.service

echo "HIVE user runtime bootstrap complete."
