# Cloud Deployment

This project is currently prepared for a split cloud deployment:

```text
Frontend cloud:
  Vercel, Netlify, or Firebase Hosting

Backend cloud:
  Strong Ubuntu VPS with Docker Compose
  OpenClaw running on the same VPS host through systemd or a separate service
```

## Backend

Use local runtime mode in production until the Dedalus provider is revisited:

```env
HIVE_RUNTIME_MODE=local
```

The backend container stores state and MemPalace data in `/app/data`, mounted through the `hive_backend_data` Docker volume.

Backend public traffic should flow through a reverse proxy:

```text
https://api.yourdomain.com -> 127.0.0.1:8010 -> hive-backend container
```

Do not expose port `8010` directly to the public internet.

### Backend Environment

Create `backend/.env` on the server from `backend/.env.example`.

Important production values:

```env
HIVE_RUNTIME_MODE=local
HIVE_AUTH_REQUIRED=true
FIREBASE_PROJECT_ID=your_firebase_project_id
HIVE_CORS_ORIGINS=https://hive-mind-livid.vercel.app

OPENCLAW_URL=http://host.docker.internal:18789/v1/chat/completions
OPENCLAW_HEALTH_URL=http://host.docker.internal:18789/
OPENCLAW_CHAT_MODEL=openclaw
OPENCLAW_PROVIDER_MODEL=google/gemini-3-flash-preview
HIVE_OPENCLAW_BOOTSTRAP_STATUS=deferred

GEMINI_API_KEY=your_key

HIVE_MEMPALACE_ENABLED=true
HIVE_STATE_PATH=/app/data/hive_state.json
HIVE_MEMPALACE_PATH=/app/data/mempalace
```

`HIVE_OPENCLAW_BOOTSTRAP_STATUS=deferred` prevents the backend container from trying to launch OpenClaw itself. The backend should talk to the OpenClaw gateway already running on the host.

### Run Backend

From the repo root:

```bash
docker compose up --build -d
docker compose logs -f hive-backend
curl http://127.0.0.1:8010/health
```

## OpenClaw

Run OpenClaw on the backend VPS host, not inside the backend container at first.

Keep it bound locally:

```text
127.0.0.1:18789
```

The backend container reaches it through:

```text
host.docker.internal:18789
```

The Compose file includes:

```yaml
extra_hosts:
  - "host.docker.internal:host-gateway"
```

### Install OpenClaw On The VPS

You only need to install OpenClaw once per backend server. After that, systemd should keep it running.

Recommended shape:

```text
host systemd: openclaw-gateway -> 127.0.0.1:18789
Docker: hive-backend -> host.docker.internal:18789
public internet -> never talks directly to OpenClaw
```

Install Node.js 20+ and OpenClaw on the host:

```bash
node --version
npm --version
npm install -g openclaw@latest
openclaw --version
```

Configure OpenClaw from the backend directory:

```bash
cd /path/to/Hive_mind/Hive_mind/backend
export GEMINI_API_KEY=your_key
export OPENCLAW_PROVIDER_MODEL=google/gemini-3-flash-preview
./scripts/openclaw_cloud_configure.sh
```

Start it once manually to test:

```bash
openclaw gateway run --auth none --bind loopback --port 18789
```

In a second terminal:

```bash
curl http://127.0.0.1:18789/
```

Then install the systemd unit. Edit `deploy/openclaw-gateway.service` first so `User`, `WorkingDirectory`, `HOME`, and `OPENCLAW_STATE_DIR` match the VPS user and repo path.

```bash
sudo cp deploy/openclaw-gateway.service /etc/systemd/system/openclaw-gateway.service
sudo systemctl daemon-reload
sudo systemctl enable --now openclaw-gateway
sudo systemctl status openclaw-gateway
journalctl -u openclaw-gateway -f
```

Verify from the backend container:

```bash
docker compose exec hive-backend python - <<'PY'
import httpx
print(httpx.get("http://host.docker.internal:18789/", timeout=5).status_code)
PY
```

## Frontend

Deploy the frontend from `frontend/` to Vercel, Netlify, or Firebase Hosting.

Use:

```bash
npm install
npm run build
```

Build output:

```text
frontend/dist
```

Set frontend production env:

```env
VITE_HIVE_API_BASE=https://api.yourdomain.com
```

The backend must allow the frontend origin:

```env
HIVE_CORS_ORIGINS=https://hive-mind-livid.vercel.app
```

## Domain Layout

Recommended:

```text
Frontend: https://app.yourdomain.com
Backend:  https://api.yourdomain.com
```

Current frontend deployment:

```text
https://hive-mind-livid.vercel.app
```

## Reverse Proxy

Example Caddy route:

```caddy
api.yourdomain.com {
    reverse_proxy 127.0.0.1:8010
}
```

## Persistent Data

Back up the backend Docker volume regularly. It contains:

```text
hive_state.json
mempalace/
telegram worker logs and pid files
openclaw health/log metadata
```

For larger production use, migrate state from JSON files to Postgres and memory to a managed vector database or dedicated Chroma/Qdrant service.
