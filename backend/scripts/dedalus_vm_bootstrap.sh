#!/usr/bin/env bash
set -euo pipefail

# Bootstrap script intended to run inside a Dedalus Machine execution.
# Dedalus Machines may expose a read-only root filesystem, so this script avoids
# apt, /opt, and systemd by default. Everything runs from a writable user-space
# directory discovered at runtime.

RUNTIME_HOME="${DEDALUS_HOME:-${HOME:-}}"
if [ -z "$RUNTIME_HOME" ] || [ ! -d "$RUNTIME_HOME" ] || [ ! -w "$RUNTIME_HOME" ]; then
  RUNTIME_HOME="/home/machine"
  mkdir -p "$RUNTIME_HOME"
fi

RAW_APP_DIR="${HIVE_REMOTE_APP_DIR:-$RUNTIME_HOME/hive-brain}"
REPO_URL="${HIVE_REPO_URL:-}"
BACKEND_SUBDIR="${HIVE_BACKEND_SUBDIR:-backend}"
case "$RAW_APP_DIR" in
  '$HOME'/*)
    APP_DIR="$RUNTIME_HOME/${RAW_APP_DIR#'$HOME'/}"
    ;;
  '~'/*)
    APP_DIR="$RUNTIME_HOME/${RAW_APP_DIR#'~'/}"
    ;;
  *)
    APP_DIR="$RAW_APP_DIR"
    ;;
esac
RUN_DIR="$APP_DIR/.hive-run"
LOG_DIR="$APP_DIR/.hive-logs"
NPM_PREFIX="$APP_DIR/.npm-global"

if [ -z "$REPO_URL" ]; then
  echo "Set HIVE_REPO_URL before running this bootstrap script." >&2
  exit 1
fi

need_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Required command is missing in the Dedalus Machine: $1" >&2
    exit 127
  fi
}

need_command git
need_command python3

if command -v sudo >/dev/null 2>&1; then
  sudo chown -R machine:machine "$RUNTIME_HOME"
else
  chown -R machine:machine "$RUNTIME_HOME"
fi

mkdir -p "$RUNTIME_HOME/.tmp" "$RUNTIME_HOME/.local/bin" "$RUNTIME_HOME/.cargo/bin"

if command -v apt-get >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update && sudo apt-get install -y python3-venv python3-pip
  else
    apt-get update && apt-get install -y python3-venv python3-pip
  fi
fi

mkdir -p "$RUNTIME_HOME/.npm-global" "$RUNTIME_HOME/.npm-cache" "$RUNTIME_HOME/.openclaw" "$RUNTIME_HOME/.compile-cache" "$RUNTIME_HOME/.hive-logs" "$RUNTIME_HOME/.hive-run"

git config --global --add safe.directory "$APP_DIR" >/dev/null 2>&1 || true

if [ ! -d "$APP_DIR/.git" ]; then
  parent_dir="$(dirname "$APP_DIR")"
  mkdir -p "$parent_dir"
  if [ -e "$APP_DIR" ]; then
    backup_dir="${APP_DIR}.bootstrap-backup-$(date +%s)"
    echo "Existing non-git app dir found at $APP_DIR; moving it to $backup_dir" >&2
    mv "$APP_DIR" "$backup_dir"
  fi
  git clone "$REPO_URL" "$APP_DIR"
else
  git -C "$APP_DIR" pull --ff-only
fi
git config --global --add safe.directory "$APP_DIR" >/dev/null 2>&1 || true

mkdir -p "$RUN_DIR" "$LOG_DIR" "$NPM_PREFIX/bin"

cd "$APP_DIR/$BACKEND_SUBDIR"

rm -rf .venv
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

OPENCLAW_STATUS="deferred"
export PATH="$NPM_PREFIX/bin:$PATH"

if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
  export npm_config_prefix="$NPM_PREFIX"
  if ! command -v openclaw >/dev/null 2>&1; then
    npm install -g openclaw
  fi
  OPENCLAW_STATUS="installed"
else
  echo "Node/npm not found; OpenClaw install deferred. HIVE backend will still start." >&2
fi

mkdir -p data

cat > .env <<EOF
HIVE_STATE_PATH=data/hive_state.json
HIVE_RUNTIME_MODE=dedalus_worker
HIVE_MEMPALACE_ENABLED=true
HIVE_MEMPALACE_PATH=data/mempalace
HIVE_MEMPALACE_AGENT=hive_brain
HIVE_OPENCLAW_BOOTSTRAP_STATUS=$OPENCLAW_STATUS
OPENCLAW_URL=http://127.0.0.1:18789/v1/chat/completions
OPENCLAW_HEALTH_URL=http://127.0.0.1:18789/
OPENCLAW_CHAT_MODEL=openclaw
OPENCLAW_PROVIDER_MODEL=${OPENCLAW_PROVIDER_MODEL:-google/gemini-3-flash-preview}
GEMINI_API_KEY=${GEMINI_API_KEY:-}
PATH=$NPM_PREFIX/bin:$PATH
EOF

if [ -f "$RUN_DIR/hive-backend.pid" ]; then
  old_pid="$(cat "$RUN_DIR/hive-backend.pid" || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" >/dev/null 2>&1; then
    kill "$old_pid" || true
    sleep 2
  fi
fi

nohup env PATH="$NPM_PREFIX/bin:$PATH" \
  "$APP_DIR/$BACKEND_SUBDIR/.venv/bin/uvicorn" main:app \
  --host 0.0.0.0 \
  --port 8010 \
  > "$LOG_DIR/hive-backend.log" \
  2>&1 &

echo "$!" > "$RUN_DIR/hive-backend.pid"

sleep 3
if ! kill -0 "$(cat "$RUN_DIR/hive-backend.pid")" >/dev/null 2>&1; then
  echo "hive-backend failed to stay running. Logs:" >&2
  tail -n 120 "$LOG_DIR/hive-backend.log" >&2 || true
  exit 1
fi

echo "HIVE user runtime bootstrap complete."
echo "Backend log: $LOG_DIR/hive-backend.log"
