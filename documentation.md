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

## Dedalus User Runtimes

The backend now has a control-plane layer for one isolated runtime per `user_id`.

In local development:

```env
HIVE_RUNTIME_MODE=local
```

Agent creation records a local runtime and continues to run OpenClaw and Telegram workers on the current machine.

For Dedalus provisioning:

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

The VM bootstrap template is:

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

## Next Steps

1. Connect the teammate webapp to `POST /agents`.
2. Add a worker manager that can run/pause Telegram workers per agent.
3. Add Dedalus provisioning for per-agent VM deployment.
4. Add Chrome extension or browser ingestion.
5. Replace JSON routing state with SQLite when concurrency matters.
