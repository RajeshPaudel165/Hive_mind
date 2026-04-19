from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

import memory_store
import dedalus_runtime
import openclaw_manager
import telegram_worker_manager
from openclaw_client import (
    OpenClawUnavailable,
    chat_completion,
    generate_pulse_message,
    get_openclaw_status,
)


app = FastAPI(
    title="HIVE BRAIN Harness",
    version="0.1.0",
    description="Minimal local MVP backend for pairing, memory ingestion, and pulse previews.",
)


def parse_cors_origins() -> list[str]:
    raw = os.getenv(
        "HIVE_CORS_ORIGINS",
        "http://127.0.0.1:3000,http://localhost:3000,"
        "http://127.0.0.1:5173,http://localhost:5173,"
        "http://127.0.0.1:5174,http://localhost:5174",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


app.add_middleware(
    CORSMiddleware,
    allow_origins=parse_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AgentInput(BaseModel):
    user_id: str | None = Field(default=None, min_length=1, max_length=200)
    user_name: str = Field(min_length=1, max_length=120)
    agent_name: str = Field(min_length=1, max_length=120)
    agent_role: str = Field(
        default="Helpful private AI companion.",
        min_length=1,
        max_length=4000,
    )
    telegram_bot_token: str = Field(min_length=20, max_length=300)
    start_openclaw: bool = True
    start_telegram_worker: bool = True


class PairTelegram(BaseModel):
    chat_id: str = Field(min_length=1, max_length=120)


class GoalInput(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)


class IngestInput(BaseModel):
    title: str = Field(default="Untitled", max_length=200)
    text: str = Field(min_length=1, max_length=50000)
    source_url: str | None = Field(default=None, max_length=2000)


class MemorySearchInput(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    n_results: int = Field(default=5, ge=1, le=20)


class OpenClawTestInput(BaseModel):
    message: str = Field(
        default="Reply in one short sentence: OpenClaw is connected.",
        min_length=1,
        max_length=2000,
    )


class RuntimeEnsureInput(BaseModel):
    user_id: str = Field(min_length=1, max_length=200)


def get_session_or_404(pairing_code: str) -> dict[str, Any]:
    try:
        return memory_store.get_session(pairing_code)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent or session")


def update_session(pairing_code: str, updates: dict[str, Any]) -> dict[str, Any]:
    try:
        return memory_store.update_session(pairing_code, updates)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent or session")


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "state_path": str(memory_store.STATE_PATH),
    }


@app.get("/integrations/openclaw/health")
def openclaw_health() -> dict[str, Any]:
    return openclaw_manager.get_status()


@app.post("/integrations/openclaw/start")
def openclaw_start() -> dict[str, Any]:
    return openclaw_manager.start_gateway()


@app.post("/integrations/openclaw/ensure")
def openclaw_ensure() -> dict[str, Any]:
    return openclaw_manager.ensure_running()


@app.post("/integrations/openclaw/stop")
def openclaw_stop() -> dict[str, Any]:
    return openclaw_manager.stop_gateway()


@app.post("/integrations/openclaw/test")
def openclaw_test(payload: OpenClawTestInput) -> dict[str, Any]:
    try:
        reply = chat_completion(
            [
                {
                    "role": "system",
                    "content": "You are a concise integration test responder.",
                },
                {"role": "user", "content": payload.message},
            ],
            timeout=20,
        )
        return {
            "ok": True,
            "reply": reply,
            "status": get_openclaw_status(),
        }
    except OpenClawUnavailable as exc:
        return {
            "ok": False,
            "error": str(exc),
            "status": get_openclaw_status(),
        }


@app.get("/integrations/mempalace/health")
def mempalace_health() -> dict[str, Any]:
    return memory_store.get_mempalace_status()


@app.get("/pulses/status")
def pulse_status() -> dict[str, Any]:
    return memory_store.get_pulse_status()


@app.get("/runtimes")
def list_user_runtimes() -> dict[str, Any]:
    return {
        "mode": dedalus_runtime.RUNTIME_MODE,
        "runtimes": memory_store.list_user_runtimes(),
    }


@app.get("/users/{user_id}/runtime")
def get_user_runtime(user_id: str) -> dict[str, Any]:
    return dedalus_runtime.get_runtime_status(user_id)


@app.post("/users/{user_id}/runtime/ensure")
def ensure_user_runtime(user_id: str) -> dict[str, Any]:
    try:
        return dedalus_runtime.ensure_user_runtime(user_id)
    except dedalus_runtime.DedalusRuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.delete("/users/{user_id}/runtime")
def delete_user_runtime(user_id: str) -> dict[str, Any]:
    return dedalus_runtime.destroy_user_runtime(user_id)


@app.post("/users/{user_id}/runtime/bootstrap")
def bootstrap_user_runtime(user_id: str) -> dict[str, Any]:
    try:
        return dedalus_runtime.start_user_runtime_bootstrap(user_id)
    except dedalus_runtime.DedalusRuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/users/{user_id}/runtime/bootstrap")
def get_user_runtime_bootstrap(user_id: str) -> dict[str, Any]:
    try:
        return dedalus_runtime.get_user_runtime_bootstrap_status(user_id)
    except dedalus_runtime.DedalusRuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/")
def root() -> dict[str, Any]:
    return {
        "name": "HIVE BRAIN Harness",
        "status": "ok",
        "docs": "/docs",
        "endpoints": {
            "health": "GET /health",
            "openclaw_health": "GET /integrations/openclaw/health",
            "openclaw_start": "POST /integrations/openclaw/start",
            "openclaw_ensure": "POST /integrations/openclaw/ensure",
            "openclaw_stop": "POST /integrations/openclaw/stop",
            "openclaw_test": "POST /integrations/openclaw/test",
            "mempalace_health": "GET /integrations/mempalace/health",
            "pulse_status": "GET /pulses/status",
            "list_runtimes": "GET /runtimes",
            "user_runtime": "GET /users/{user_id}/runtime",
            "ensure_user_runtime": "POST /users/{user_id}/runtime/ensure",
            "delete_user_runtime": "DELETE /users/{user_id}/runtime",
            "bootstrap_user_runtime": "POST /users/{user_id}/runtime/bootstrap",
            "bootstrap_status": "GET /users/{user_id}/runtime/bootstrap",
            "list_agents": "GET /agents",
            "create_agent": "POST /agents",
            "get_agent": "GET /agents/{agent_id}",
            "delete_agent": "DELETE /agents/{agent_id}",
            "agent_context": "GET /agents/{agent_id}/context",
            "agent_ingest": "POST /agents/{agent_id}/ingest",
            "agent_memory_search": "POST /agents/{agent_id}/memory/search",
            "agent_memory_backfill": "POST /agents/{agent_id}/memory/backfill",
            "agent_pulse_preview": "POST /agents/{agent_id}/pulse",
        },
    }


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HIVE BRAIN Harness</title>
  <style>
    :root {
      color-scheme: light;
      font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7f9;
      color: #172026;
    }
    * { box-sizing: border-box; }
    body { margin: 0; }
    main {
      width: min(1100px, calc(100% - 32px));
      margin: 32px auto;
    }
    header {
      display: grid;
      gap: 10px;
      margin-bottom: 28px;
    }
    h1 {
      margin: 0;
      font-size: 34px;
      line-height: 1.1;
      letter-spacing: 0;
    }
    h2 {
      margin: 0 0 14px;
      font-size: 19px;
      letter-spacing: 0;
    }
    p { margin: 0; color: #52616b; line-height: 1.5; }
    .grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
    }
    section {
      background: #ffffff;
      border: 1px solid #d8e0e6;
      border-radius: 8px;
      padding: 18px;
      min-width: 0;
    }
    .wide { grid-column: 1 / -1; }
    label {
      display: grid;
      gap: 7px;
      font-weight: 650;
      margin-bottom: 12px;
    }
    input, textarea {
      width: 100%;
      border: 1px solid #b8c4cc;
      border-radius: 6px;
      padding: 10px 11px;
      font: inherit;
      color: #172026;
      background: #ffffff;
    }
    textarea {
      min-height: 92px;
      resize: vertical;
    }
    button {
      border: 0;
      border-radius: 6px;
      padding: 10px 13px;
      font: inherit;
      font-weight: 700;
      color: #ffffff;
      background: #146c63;
      cursor: pointer;
    }
    button.secondary { background: #33424d; }
    button:disabled { opacity: 0.65; cursor: not-allowed; }
    .actions { display: flex; flex-wrap: wrap; gap: 10px; }
    .status-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
    }
    .status {
      border: 1px solid #d8e0e6;
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfd;
      min-height: 86px;
    }
    .status strong { display: block; margin-bottom: 6px; }
    .ok { color: #0f766e; }
    .warn { color: #b45309; }
    code, pre {
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", monospace;
    }
    pre {
      white-space: pre-wrap;
      overflow-wrap: anywhere;
      background: #101820;
      color: #f5f7f9;
      border-radius: 8px;
      padding: 14px;
      max-height: 320px;
      overflow: auto;
    }
    .pairing-code {
      display: inline-block;
      margin: 12px 0;
      padding: 8px 10px;
      border-radius: 6px;
      background: #e8f3f1;
      color: #0f4f49;
      font-size: 20px;
      font-weight: 800;
      letter-spacing: 0;
    }
    .muted { color: #6b7882; font-size: 14px; }
    @media (max-width: 760px) {
      main { width: min(100% - 20px, 1100px); margin: 20px auto; }
      .grid, .status-grid { grid-template-columns: 1fr; }
      h1 { font-size: 28px; }
    }
  </style>
</head>
<body>
  <main>
    <header>
      <h1>HIVE BRAIN Harness</h1>
      <p>Create an agent, connect its Telegram bot, check memory, and preview pulses.</p>
    </header>

    <div class="grid">
      <section>
        <h2>Create Agent</h2>
        <label>
          User name
          <input id="userName" autocomplete="name" placeholder="Nobay">
        </label>
        <label>
          Agent name
          <input id="agentName" placeholder="Study Coach">
        </label>
        <label>
          Agent role
          <textarea id="agentRole" placeholder="Help me learn Fourier Analysis and keep me accountable."></textarea>
        </label>
        <label>
          Telegram bot token
          <input id="telegramToken" placeholder="1234567890:ABC...">
        </label>
        <button id="createAgent">Create agent</button>
        <div id="sessionResult"></div>
      </section>

      <section>
        <h2>Use Existing Agent</h2>
        <label>
          Agent ID
          <input id="agentId" placeholder="AGENT-1234ABCD">
        </label>
        <div class="actions">
          <button class="secondary" id="loadContext">Load context</button>
          <button class="secondary" id="pulsePreview">Preview pulse</button>
          <button class="secondary" id="backfillMemory">Backfill memory</button>
        </div>
      </section>

      <section class="wide">
        <h2>System Status</h2>
        <div class="status-grid">
          <div class="status"><strong>API</strong><span id="apiStatus">Checking...</span></div>
          <div class="status"><strong>OpenClaw</strong><span id="openclawStatus">Checking...</span></div>
          <div class="status"><strong>MemPalace</strong><span id="mempalaceStatus">Checking...</span></div>
        </div>
      </section>

      <section>
        <h2>Save Context</h2>
        <label>
          Title
          <input id="dumpTitle" placeholder="Sine Waves">
        </label>
        <label>
          Text
          <textarea id="dumpText" placeholder="Fourier analysis is about representing signals..."></textarea>
        </label>
        <button id="saveContext">Save to memory</button>
      </section>

      <section>
        <h2>Recall Memory</h2>
        <label>
          Query
          <input id="memoryQuery" placeholder="Fourier sine cosine">
        </label>
        <button id="searchMemory">Search MemPalace</button>
      </section>

      <section class="wide">
        <h2>Output</h2>
        <pre id="output">Ready.</pre>
      </section>
    </div>
  </main>

  <script>
    const $ = (id) => document.getElementById(id);

    function agentId() {
      return $("agentId").value.trim().toUpperCase();
    }

    function show(value) {
      $("output").textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    }

    function preview(text, length = 180) {
      const clean = String(text || "").replace(/\\s+/g, " ").trim();
      return clean.length > length ? `${clean.slice(0, length - 3)}...` : clean;
    }

    function showContext(context) {
      const lines = [];
      lines.push(`Agent: ${context.pairing_code}`);
      lines.push(`User: ${context.user_name}`);
      lines.push(`Role: ${context.agent_role || "Helpful private AI companion."}`);
      lines.push(`Telegram paired: ${context.telegram_paired}`);
      lines.push("");

      lines.push(`Goals (${context.goals.length})`);
      for (const goal of context.goals.slice(-5).reverse()) {
        lines.push(`- ${preview(goal.text)}`);
      }
      lines.push("");

      lines.push(`JSON notes (${context.dumps.length})`);
      for (const dump of context.dumps.slice(-10).reverse()) {
        lines.push(`- ${dump.title}: ${preview(dump.text)}`);
      }
      lines.push("");

      const mem = context.mempalace || { count: 0, results: [] };
      lines.push(`MemPalace drawers (${mem.count || 0})`);
      for (const hit of (mem.results || []).slice(0, 10)) {
        lines.push(`- ${hit.room} / ${hit.source_file}: ${preview(hit.text)}`);
      }

      show(lines.join("\\n"));
    }

    async function request(path, options = {}) {
      const response = await fetch(path, {
        headers: { "Content-Type": "application/json", ...(options.headers || {}) },
        ...options,
      });
      const text = await response.text();
      let data;
      try { data = JSON.parse(text); } catch { data = text; }
      if (!response.ok) {
        throw new Error(typeof data === "string" ? data : JSON.stringify(data));
      }
      return data;
    }

    async function refreshStatus() {
      try {
        const api = await request("/health");
        $("apiStatus").innerHTML = `<span class="ok">${api.status}</span>`;
      } catch {
        $("apiStatus").innerHTML = `<span class="warn">offline</span>`;
      }

      try {
        const openclaw = await request("/integrations/openclaw/health");
        $("openclawStatus").innerHTML = openclaw.reachable
          ? `<span class="ok">reachable</span><br><span class="muted">${openclaw.model}</span>`
          : `<span class="warn">fallback active</span>`;
      } catch {
        $("openclawStatus").innerHTML = `<span class="warn">unknown</span>`;
      }

      try {
        const mempalace = await request("/integrations/mempalace/health");
        $("mempalaceStatus").innerHTML = mempalace.reachable
          ? `<span class="ok">${mempalace.drawer_count} drawers</span><br><span class="muted">${mempalace.palace_path}</span>`
          : `<span class="warn">${mempalace.enabled === false ? "disabled" : "not ready"}</span>`;
      } catch {
        $("mempalaceStatus").innerHTML = `<span class="warn">unknown</span>`;
      }
    }

    $("createAgent").addEventListener("click", async () => {
      const userName = $("userName").value.trim();
      const agentName = $("agentName").value.trim();
      const agentRole = $("agentRole").value.trim() || "Helpful private AI companion.";
      const telegramToken = $("telegramToken").value.trim();
      if (!userName) {
        show("Enter a user name first.");
        return;
      }
      if (!agentName) {
        show("Enter an agent name first.");
        return;
      }
      if (!telegramToken) {
        show("Enter the Telegram bot token from BotFather.");
        return;
      }
      try {
        const data = await request("/agents", {
          method: "POST",
          body: JSON.stringify({
            user_name: userName,
            agent_name: agentName,
            agent_role: agentRole,
            telegram_bot_token: telegramToken,
          }),
        });
        $("agentId").value = data.agent_id;
        $("sessionResult").innerHTML = `
          <div class="pairing-code">${data.agent_id}</div>
          <p>Run <code>HIVE_AGENT_ID=${data.agent_id} python telegram_bot.py</code>, then send <code>/start</code> to that bot.</p>
        `;
        show(data);
        refreshStatus();
      } catch (error) {
        show(error.message);
      }
    });

    $("loadContext").addEventListener("click", async () => {
      if (!agentId()) return show("Enter an agent ID first.");
      try { showContext(await request(`/agents/${agentId()}/context`)); }
      catch (error) { show(error.message); }
    });

    $("pulsePreview").addEventListener("click", async () => {
      if (!agentId()) return show("Enter an agent ID first.");
      try { show(await request(`/agents/${agentId()}/pulse`, { method: "POST" })); }
      catch (error) { show(error.message); }
    });

    $("backfillMemory").addEventListener("click", async () => {
      if (!agentId()) return show("Enter an agent ID first.");
      try {
        show(await request(`/agents/${agentId()}/memory/backfill`, { method: "POST" }));
        refreshStatus();
      } catch (error) { show(error.message); }
    });

    $("saveContext").addEventListener("click", async () => {
      if (!agentId()) return show("Enter an agent ID first.");
      const title = $("dumpTitle").value.trim() || "Dashboard note";
      const text = $("dumpText").value.trim();
      if (!text) return show("Enter text to save.");
      try {
        show(await request(`/agents/${agentId()}/ingest`, {
          method: "POST",
          body: JSON.stringify({ title, text }),
        }));
        refreshStatus();
      } catch (error) { show(error.message); }
    });

    $("searchMemory").addEventListener("click", async () => {
      if (!agentId()) return show("Enter an agent ID first.");
      const query = $("memoryQuery").value.trim();
      if (!query) return show("Enter a memory search query.");
      try {
        show(await request(`/agents/${agentId()}/memory/search`, {
          method: "POST",
          body: JSON.stringify({ query, n_results: 5 }),
        }));
      } catch (error) { show(error.message); }
    });

    refreshStatus();
  </script>
</body>
</html>"""


@app.get("/agents")
def list_agents() -> dict[str, Any]:
    return {"agents": memory_store.list_agents()}


@app.post("/agents")
def create_agent(payload: AgentInput) -> dict[str, Any]:
    user_runtime = None
    if payload.user_id:
        try:
            user_runtime = dedalus_runtime.ensure_user_runtime(payload.user_id)
        except dedalus_runtime.DedalusRuntimeError as exc:
            raise HTTPException(status_code=503, detail=str(exc))

    agent = memory_store.create_agent(
        user_id=payload.user_id,
        user_name=payload.user_name,
        agent_name=payload.agent_name,
        agent_role=payload.agent_role,
        telegram_bot_token=payload.telegram_bot_token,
    )
    use_local_runtime = not (
        user_runtime and user_runtime.get("provider") == "dedalus"
    )

    openclaw_status = openclaw_manager.get_status()
    if payload.start_openclaw and use_local_runtime:
        openclaw_status = openclaw_manager.ensure_running()
    worker_status = telegram_worker_manager.get_worker_status(agent["agent_id"])
    if payload.start_telegram_worker and use_local_runtime:
        worker_status = telegram_worker_manager.start_worker(agent["agent_id"])
    return {
        **agent,
        "user_runtime": user_runtime,
        "telegram_start_instruction": "Open this Telegram bot and send /start.",
        "worker_command": telegram_worker_manager.worker_command(agent["agent_id"]),
        "openclaw": openclaw_status,
        "telegram_worker": worker_status,
        "next_step": (
            "Open this Telegram bot and send /start. The local Telegram worker "
            "starts automatically when running under the HIVE backend."
        ),
    }


@app.get("/agents/{agent_id}/telegram/status")
def get_agent_telegram_status(agent_id: str) -> dict[str, Any]:
    try:
        memory_store.get_agent(agent_id)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return telegram_worker_manager.get_worker_status(agent_id)


@app.post("/agents/{agent_id}/telegram/start")
def start_agent_telegram_worker(agent_id: str) -> dict[str, Any]:
    try:
        memory_store.get_agent(agent_id)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return telegram_worker_manager.start_worker(agent_id)


@app.post("/agents/{agent_id}/telegram/stop")
def stop_agent_telegram_worker(agent_id: str) -> dict[str, Any]:
    try:
        memory_store.get_agent(agent_id)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return telegram_worker_manager.stop_worker(agent_id)


@app.get("/agents/{agent_id}")
def get_agent(agent_id: str) -> dict[str, Any]:
    try:
        agent = memory_store.get_agent(agent_id)
        context = memory_store.get_context(agent_id)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return {"agent": agent, "context": context}


@app.delete("/agents/{agent_id}")
def delete_agent(agent_id: str) -> dict[str, Any]:
    worker_status = telegram_worker_manager.stop_worker(agent_id)
    try:
        deleted = memory_store.delete_agent(agent_id)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return {
        **deleted,
        "telegram_worker": worker_status,
        "message": "Agent deleted.",
    }


@app.get("/agents/{agent_id}/context")
def get_agent_context(agent_id: str) -> dict[str, Any]:
    try:
        return memory_store.get_context(agent_id)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent")


@app.post("/agents/{agent_id}/ingest")
def ingest_agent_dump(agent_id: str, payload: IngestInput) -> dict[str, Any]:
    try:
        memory_store.ingest_dump(
            agent_id,
            title=payload.title,
            text=payload.text,
            source_url=payload.source_url,
        )
        session = memory_store.get_session(agent_id)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent")
    return {"agent_id": agent_id, "dump_count": len(session["dumps"])}


@app.post("/agents/{agent_id}/memory/search")
def search_agent_memory(agent_id: str, payload: MemorySearchInput) -> dict[str, Any]:
    try:
        return memory_store.search_memory(
            agent_id,
            query=payload.query,
            n_results=payload.n_results,
        )
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent")


@app.post("/agents/{agent_id}/memory/backfill")
def backfill_agent_memory(agent_id: str) -> dict[str, Any]:
    try:
        return memory_store.backfill_session_to_mempalace(agent_id)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent")


@app.post("/agents/{agent_id}/pulse")
def create_agent_pulse_preview(agent_id: str) -> dict[str, Any]:
    return create_pulse_preview(agent_id)


@app.post("/sessions")
def create_session() -> dict[str, Any]:
    raise HTTPException(
        status_code=410,
        detail="Legacy session codes are disabled. Create an agent with POST /agents.",
    )


@app.post("/sessions/{pairing_code}/telegram")
def pair_telegram(pairing_code: str, payload: PairTelegram) -> dict[str, Any]:
    try:
        session = memory_store.pair_telegram(pairing_code, payload.chat_id)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent or legacy session")
    return {
        "pairing_code": pairing_code,
        "telegram_chat_id": session["telegram_chat_id"],
        "message": f"Hello {session['user_name']}. Your Hive Brain is paired.",
    }


@app.post("/sessions/{pairing_code}/telegram/activate")
def activate_telegram(pairing_code: str) -> dict[str, Any]:
    try:
        session = memory_store.activate_telegram_session(pairing_code)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent or legacy session")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {
        "pairing_code": pairing_code,
        "telegram_chat_id": session["telegram_chat_id"],
        "message": f"{pairing_code} is now the active Telegram session.",
    }


@app.post("/sessions/{pairing_code}/goals")
def add_goal(pairing_code: str, payload: GoalInput) -> dict[str, Any]:
    try:
        goal = memory_store.add_goal(pairing_code, payload.goal)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent or legacy session")
    return {"pairing_code": pairing_code, "goal": goal}


@app.post("/sessions/{pairing_code}/ingest")
def ingest_dump(pairing_code: str, payload: IngestInput) -> dict[str, Any]:
    try:
        memory_store.ingest_dump(
            pairing_code,
            title=payload.title,
            text=payload.text,
            source_url=payload.source_url,
        )
        session = memory_store.get_session(pairing_code)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent or legacy session")
    return {"pairing_code": pairing_code, "dump_count": len(session["dumps"])}


@app.get("/sessions/{pairing_code}/context")
def get_context(pairing_code: str) -> dict[str, Any]:
    try:
        return memory_store.get_context(pairing_code)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent or legacy session")


@app.post("/sessions/{pairing_code}/memory/search")
def search_memory(pairing_code: str, payload: MemorySearchInput) -> dict[str, Any]:
    try:
        return memory_store.search_memory(
            pairing_code,
            query=payload.query,
            n_results=payload.n_results,
        )
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent or legacy session")


@app.post("/sessions/{pairing_code}/memory/backfill")
def backfill_memory(pairing_code: str) -> dict[str, Any]:
    try:
        return memory_store.backfill_session_to_mempalace(pairing_code)
    except memory_store.UnknownSession:
        raise HTTPException(status_code=404, detail="Unknown agent or legacy session")


@app.post("/sessions/{pairing_code}/pulse")
def create_pulse_preview(pairing_code: str) -> dict[str, Any]:
    session = get_session_or_404(pairing_code)
    goals = session["goals"]
    dumps = session["dumps"]

    if not goals:
        raise HTTPException(status_code=400, detail="Add a goal before creating a pulse")

    latest_goal = goals[-1]["text"]
    latest_dump = dumps[-1]["title"] if dumps else "your saved context"
    enriched_dumps = [*dumps]
    mempalace_results = None
    try:
        mempalace_results = memory_store.search_memory(pairing_code, latest_goal, n_results=3)
        for hit in mempalace_results.get("results", []):
            enriched_dumps.append(
                {
                    "_source": "mempalace",
                    "title": hit.get("source_file", "MemPalace hit"),
                    "text": hit.get("text", ""),
                    "source_url": None,
                    "created_at": hit.get("created_at"),
                }
            )
    except Exception:
        mempalace_results = None

    message = (
        f"Quick check-in on your goal: {latest_goal}. "
        f"You recently saved {latest_dump}; want to spend 10 minutes reviewing it now?"
    )
    delivery = "preview_fallback"
    error = None

    try:
        session_for_prompt = {**session, "dumps": enriched_dumps}
        message = generate_pulse_message(session_for_prompt)
        delivery = "openclaw_preview"
    except OpenClawUnavailable as exc:
        error = str(exc)

    response = {
        "pairing_code": pairing_code,
        "telegram_chat_id": session["telegram_chat_id"],
        "message": message,
        "delivery": delivery,
        "mempalace_attached": bool(mempalace_results and mempalace_results.get("results")),
    }
    if error:
        response["fallback_reason"] = error

    return response
