# OpenClaw Local Runbook

This project uses OpenClaw through its OpenAI-compatible HTTP endpoint:

```text
POST http://127.0.0.1:18789/v1/chat/completions
```

The same shape should be used later inside each Dedalus VM: one VM runs its own OpenClaw gateway, MemPalace, Telegram worker, and pulse worker.

## Fresh Local Setup

From the backend folder:

```bash
cd /home/nobay/Hive_mind/Hive_mind/backend
```

Configure OpenClaw:

```bash
scripts/openclaw_local_configure.sh
```

By default, HIVE BRAIN configures OpenClaw to use:

```text
google/gemini-3-flash-preview
```

Put your Gemini API key in backend `.env`:

```env
GEMINI_API_KEY=...
OPENCLAW_CHAT_MODEL=openclaw
OPENCLAW_PROVIDER_MODEL=google/gemini-3-flash-preview
```

`GOOGLE_API_KEY` is also supported as an alias if your local Google/Gemini tooling expects it.

Then run:

```bash
scripts/openclaw_local_configure.sh
```

Start the gateway:

```bash
scripts/openclaw_local_start.sh
```

Check status from another terminal:

```bash
scripts/openclaw_local_status.sh
```

Check through the HIVE backend:

```bash
curl -s http://127.0.0.1:8010/integrations/openclaw/health
```

Run a direct HIVE integration test:

```bash
curl -s -X POST http://127.0.0.1:8010/integrations/openclaw/test \
  -H "Content-Type: application/json" \
  -d '{"message":"Reply in one sentence: OpenClaw is connected."}'
```

## Dedalus Shape Later

For multi-user Dedalus deployment, do not share one OpenClaw gateway across users. The intended runtime shape is:

```text
agent/user
  -> dedicated Dedalus VM
      -> OpenClaw gateway on 127.0.0.1:18789
      -> MemPalace local data
      -> Telegram worker for that agent token
      -> pulse worker
```

The harness should provision the VM, install/configure OpenClaw, then configure the agent runtime to call that VM-local gateway.
