# HIVE BRAIN Documentation

## Overview

HIVE BRAIN is a local-first agentic harness for a proactive, stateful AI companion. The current MVP is agent-first: each agent owns its Telegram bot token, has a dedicated memory namespace, and can receive proactive pulse messages.

The product loop is:

1. Create an agent with a user name, agent name, and Telegram bot token.
2. Run the Telegram worker for that agent with `HIVE_AGENT_ID`.
3. The user sends `/start` to their own bot.
4. The first normal Telegram message becomes the active goal.
5. Later normal Telegram messages become saved context.
6. Goals and context are mirrored into MemPalace.
7. `/recall` searches MemPalace from Telegram.
8. `/pulse` or the pulse worker generates a proactive check-in.

## Architecture

```text
FastAPI dashboard/API
  -> creates agents
  -> stores agent config and routing state

Telegram bot worker
  -> runs with HIVE_AGENT_ID
  -> loads that agent's Telegram bot token
  -> routes messages to that agent

memory_store.py
  -> JSON state for agent routing and lightweight metadata
  -> mirrors goals/context into MemPalace

MemPalace
  -> searchable local memory per agent

OpenClaw
  -> optional LLM pulse generation
  -> deterministic fallback when unavailable

pulse_worker.py
  -> scheduled proactive Telegram delivery
```

## Components

- `main.py`: FastAPI routes and built-in dashboard.
- `telegram_bot.py`: Telegram long-polling worker for one agent.
- `pulse_worker.py`: scheduled proactive pulse sender.
- `memory_store.py`: agent/session state, routing, and MemPalace mirroring.
- `mempalace_memory.py`: MemPalace adapter using the Python API.
- `openclaw_client.py`: OpenClaw chat-completions client with fallback handling.
- `.env`: local runtime config and secrets.
- `.env.example`: safe config template.

## Agent Model

The current model is:

```text
agent_id -> Telegram bot token -> Telegram chat id -> MemPalace wing
```

Example agent id:

```text
AGENT-1234ABCD
```

Each agent also has a backing internal session with the same id. That keeps existing memory, pulse, and context code simple while keeping the product flow agent-first.

## Environment

Backend path:

```bash
cd /home/nobay/Hive_mind/Hive_mind/backend
```

Important `.env` values:

```env
HIVE_STATE_PATH=data/hive_state.json
HIVE_CORS_ORIGINS=http://127.0.0.1:3000,http://localhost:3000,http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174

HIVE_RUNTIME_MODE=local
DEDALUS_API_KEY=...
DEDALUS_ORG_ID=
DEDALUS_MACHINE_VCPU=1
DEDALUS_MACHINE_MEMORY_MIB=2048
DEDALUS_MACHINE_STORAGE_GIB=10
DEDALUS_BOOTSTRAP_TIMEOUT_MS=1800000
DEDALUS_BOOTSTRAP_PREVIEW_VISIBILITY=private
HIVE_REPO_URL=https://github.com/your-org/your-repo.git
DEDALUS_HOME=/home/machine
HIVE_REMOTE_APP_DIR=/home/machine/hive-brain
HIVE_BACKEND_SUBDIR=backend

OPENCLAW_URL=http://127.0.0.1:18789/v1/chat/completions
OPENCLAW_HEALTH_URL=http://127.0.0.1:18789/
OPENCLAW_CHAT_MODEL=openclaw
OPENCLAW_PROVIDER_MODEL=google/gemini-3-flash-preview
OPENCLAW_TIMEOUT_SECONDS=45

GEMINI_API_KEY=...

TELEGRAM_API_BASE=https://api.telegram.org
TELEGRAM_POLL_TIMEOUT_SECONDS=30
HIVE_SAVE_ASSISTANT_REPLIES=true

HIVE_PULSE_INTERVAL_SECONDS=3600
HIVE_PULSE_LOOP_SLEEP_SECONDS=30

HIVE_MEMPALACE_ENABLED=true
HIVE_MEMPALACE_PATH=data/mempalace
HIVE_MEMPALACE_AGENT=hive_brain
```

For an individual Telegram worker, run with:

```bash
HIVE_AGENT_ID=AGENT-1234ABCD python telegram_bot.py
```

The bot token is loaded from the agent record.

## Runbook

Run the API:

```bash
cd /home/nobay/Hive_mind/Hive_mind/backend
uvicorn main:app --host 127.0.0.1 --port 8010 --reload
```

Open the dashboard:

```text
http://127.0.0.1:8010/dashboard
```

Run a Telegram worker for one agent:

```bash
cd /home/nobay/Hive_mind/Hive_mind/backend
HIVE_AGENT_ID=AGENT-1234ABCD python telegram_bot.py
```

Run scheduled pulses:

```bash
cd /home/nobay/Hive_mind/Hive_mind/backend
python pulse_worker.py
```

For fast local pulse testing:

```env
HIVE_PULSE_INTERVAL_SECONDS=60
HIVE_PULSE_LOOP_SLEEP_SECONDS=10
```

## API Routes

Health:

```text
GET  /
GET  /dashboard
GET  /health
GET  /integrations/openclaw/health
POST /integrations/openclaw/start
POST /integrations/openclaw/ensure
POST /integrations/openclaw/stop
GET  /integrations/mempalace/health
GET  /pulses/status
GET  /runtimes
GET  /users/{user_id}/runtime
POST /users/{user_id}/runtime/ensure
DELETE /users/{user_id}/runtime
POST /users/{user_id}/runtime/bootstrap
GET  /users/{user_id}/runtime/bootstrap
```

Agents:

```text
GET  /agents
POST /agents
GET  /agents/{agent_id}
DELETE /agents/{agent_id}
GET  /agents/{agent_id}/context
POST /agents/{agent_id}/ingest
POST /agents/{agent_id}/memory/search
POST /agents/{agent_id}/memory/backfill
POST /agents/{agent_id}/pulse
GET  /agents/{agent_id}/telegram/status
POST /agents/{agent_id}/telegram/start
POST /agents/{agent_id}/telegram/stop
```

Create an agent:

```bash
curl -s -X POST http://127.0.0.1:8010/agents \
  -H "Content-Type: application/json" \
  -d '{
    "user_id":"user_123",
    "user_name":"Nobay",
    "agent_name":"Study Coach",
    "agent_role":"Help me learn Fourier Analysis and keep me accountable.",
    "telegram_bot_token":"<bot-token-from-botfather>"
  }'
```

Search memory:

```bash
curl -s -X POST http://127.0.0.1:8010/agents/AGENT-1234ABCD/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query":"Fourier sine cosine","n_results":3}'
```

Preview a pulse:

```bash
curl -s -X POST http://127.0.0.1:8010/agents/AGENT-1234ABCD/pulse
```

## Telegram Commands

Connect the bot:

```text
/start
```

After `/start`, the first normal message becomes the active goal:

```text
Learn Fourier Analysis in 30 days
```

Later normal messages are saved as context, searched against MemPalace, sent to OpenClaw with the agent's goals and relevant memory, and answered back in Telegram:

```text
Fourier series breaks signals into sine and cosine waves.
```

By default, assistant replies are saved back into memory as `Assistant reply` context. Disable that with:

```bash
HIVE_SAVE_ASSISTANT_REPLIES=false
```

Explicit commands:

```text
/goal Learn linear algebra
/save Sine Waves | Fourier analysis is about representing signals with trigonometric functions.
/recall Fourier sine cosine
/pulse
```

## OpenClaw

OpenClaw is called at:

```text
POST http://127.0.0.1:18789/v1/chat/completions
```

When an agent is created from the webapp, the backend calls `POST /integrations/openclaw/ensure` internally. If the gateway is not reachable, HIVE starts `scripts/openclaw_local_start.sh` as a managed background process and writes logs to:

```text
/home/nobay/Hive_mind/Hive_mind/backend/data/openclaw_logs/gateway.log
```

If OpenClaw is unavailable, pulse generation returns a deterministic fallback with:

```json
"delivery": "preview_fallback"
```

If OpenClaw succeeds:

```json
"delivery": "openclaw_preview"
```

## User Runtimes

The backend has a control-plane layer for one runtime record per `user_id`.

Use local runtime mode for the current product path:

```env
HIVE_RUNTIME_MODE=local
```

Agent creation records a local runtime and continues to run OpenClaw and Telegram workers on the current machine.

Dedalus provisioning is currently experimental. Provisioning works, but bootstrap has been unreliable in the VM environment because of filesystem ownership, read-only temp paths, package cache I/O errors, and toolchain install behavior. Do not block core agent/dashboard work on Dedalus.

For future Dedalus testing:

```env
HIVE_RUNTIME_MODE=dedalus
DEDALUS_API_KEY=<key from Dedalus>
DEDALUS_MACHINE_VCPU=1
DEDALUS_MACHINE_MEMORY_MIB=2048
DEDALUS_MACHINE_STORAGE_GIB=10
```

Then:

```text
POST /users/{user_id}/runtime/ensure
```

creates or returns that user's Dedalus Machine runtime. `POST /agents` also ensures the user runtime when `user_id` is provided.

After the machine is running:

```text
POST /users/{user_id}/runtime/bootstrap
```

starts a step-by-step Dedalus bootstrap. The control-plane runs named VM executions so each failure reports the exact phase that failed. Current order:

```text
fix-home-ownership
prepare-uv-directories
install-uv
prepare-runtime-directories
clone-or-update-repo
install-python-requirements
install-node-if-missing
install-openclaw
configure-openclaw
write-hive-env
start-openclaw
start-hive-backend
verify-hive-backend
```

The first step runs:

```bash
sudo chown -R machine:machine /home/machine
```

This fixes ownership only; it does not create missing directories. The next step creates only the directories needed by the official `uv` installer:

```bash
mkdir -p /home/machine/.tmp /home/machine/.local/bin /home/machine/.cargo/bin
```

`/home/machine/.tmp` is required because Dedalus can expose `/tmp` as read-only, and the bootstrap exports:

```bash
TMPDIR=/home/machine/.tmp
```

The `install-uv` step then runs:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
source "$HOME/.local/bin/env"
```

The Python dependency step uses the VM's existing Python and disables uv-managed Python downloads:

```bash
export UV_PYTHON_DOWNLOADS=never
uv venv .venv --python /usr/bin/python3
uv pip install --refresh --python .venv/bin/python -r requirements.txt
```

Runtime directories are created after uv is installed:

```text
/home/machine/.npm-global
/home/machine/.npm-cache
/home/machine/.uv-cache
/home/machine/.openclaw
/home/machine/.compile-cache
/home/machine/.hive-logs
/home/machine/.hive-run
```

Poll bootstrap status with:

```text
GET /users/{user_id}/runtime/bootstrap
```

When bootstrap succeeds, HIVE creates a Dedalus preview for port `8010` and stores the returned `runtime_url`. If a step fails, the runtime record includes `bootstrap_steps`, `bootstrap_execution`, and `bootstrap_output` so the failed phase is visible directly from the status endpoint.

The fallback VM bootstrap script is:

```text
/home/nobay/Hive_mind/Hive_mind/backend/scripts/dedalus_vm_bootstrap.sh
```

In Dedalus mode, the control-plane should not run the user's OpenClaw and Telegram workers locally. Those belong inside the user's VM after bootstrap.

## MemPalace

MemPalace was installed from the official GitHub repository into the backend `.venv` as an editable source install:

```text
/home/nobay/Hive_mind/local_test/mempalace_github
```

The local palace path is:

```text
/home/nobay/Hive_mind/Hive_mind/backend/data/mempalace
```

Agent goals go to room `goals`; notes and ingested context go to room `context`.

## Legacy Notes

The old session-code flow is disabled for new creation. Some compatibility routes still exist internally because agent ids use the same underlying memory/pulse functions, but the user-facing flow is now agent-first.

## Cloud Auth and Permissions

The backend now supports Firebase-backed API permissions for the frontend/backend split deployment.

Relevant environment variables:

```env
HIVE_AUTH_REQUIRED=true
FIREBASE_PROJECT_ID=your_firebase_project_id
HIVE_CORS_ORIGINS=https://your-frontend-domain
```

When auth is enabled, frontend requests must send:

```http
Authorization: Bearer <firebase_id_token>
```

The backend verifies the Firebase ID token using Google's secure token certificates and the configured Firebase project id. It then uses the Firebase UID as the canonical owner id for newly created agents.

Protected agent routes:

```text
GET    /agents
POST   /agents
GET    /agents/{agent_id}
DELETE /agents/{agent_id}
GET    /agents/{agent_id}/context
POST   /agents/{agent_id}/ingest
POST   /agents/{agent_id}/memory/search
POST   /agents/{agent_id}/memory/backfill
POST   /agents/{agent_id}/pulse
GET    /agents/{agent_id}/telegram/status
POST   /agents/{agent_id}/telegram/start
POST   /agents/{agent_id}/telegram/stop
```

Permissions are currently owner-based:

```text
Firebase user UID -> owns agents whose user_id matches that UID
```

That means each signed-in user sees and controls only their own agents. If a user tries to access another user's agent id, the backend returns `404 Unknown agent` instead of exposing that the agent exists.

For local development, `HIVE_AUTH_REQUIRED=false` keeps the backend permissive so curl testing and local dashboard work without Firebase tokens.

## Tool Permissions

Each agent now has a tool permission policy stored in backend state.

Default policy:

```text
memory_read: allow
memory_write: allow
pulse: allow
openclaw_chat: allow
telegram_send: allow
brave_search: ask
gmail: ask
calendar: ask
notion: ask
todo: allow
notes: allow
filesystem: deny
browser: deny
shell: deny
```

Allowed states:

```text
allow
ask
deny
```

`ask` is reserved for the approval queue. Until an approval queue exists, backend actions treat `ask` as blocked.

HTTP control:

```text
GET /agents/{agent_id}/permissions
PUT /agents/{agent_id}/permissions
POST /agents/{agent_id}/permissions/reset
```

Example update:

```json
{
  "permissions": {
    "memory_read": "deny",
    "shell": "ask"
  }
}
```

Currently enforced:

```text
memory_read -> context loading, memory search, Telegram /recall, memory attached to replies
memory_write -> ingest, goals, backfill, Telegram /goal, /save, saved Telegram messages
pulse -> pulse previews and Telegram /pulse
openclaw_chat -> normal Telegram agent replies and OpenClaw-generated pulse text
brave_search/gmail/calendar/notion/todo/notes -> OpenClaw-style extension intent policy
```

The dashboard can edit the policy from each agent card. Telegram can edit the same policy with:

```text
/permission
/permission allow memory_read
/permission ask shell
/permission deny filesystem
/permission reset
```

Permission changes append to a per-agent audit list in backend state.

For OpenClaw turns, HIVE now attaches the agent role plus the current tool permission policy to the OpenClaw prompt. This gives the model a clear capability manifest:

```text
allow -> the agent may use or suggest the capability
ask -> the agent should ask the user to approve it first
deny -> the agent must not use the capability
```

The current integration still talks to OpenClaw through the chat-completions endpoint. That means this is prompt-level control for OpenClaw skills/plugins. Native hard limits should be added next by mapping HIVE permissions into OpenClaw plugin/MCP/approval configuration per agent.

## Next Steps

1. Deploy backend on a stronger DigitalOcean droplet with Docker Compose.
2. Deploy frontend separately with `VITE_HIVE_API_BASE` pointing at the backend domain.
3. Add the approval queue for `ask` permissions.
4. Map HIVE permissions into native OpenClaw plugins/MCP/approvals per agent.
5. Replace JSON routing state with SQLite/Postgres when concurrency matters.
