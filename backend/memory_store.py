from __future__ import annotations

import json
import os
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import mempalace_memory


BACKEND_DIR = Path(__file__).resolve().parent


def resolve_backend_path(value: str) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    return BACKEND_DIR / path


STATE_PATH = resolve_backend_path(os.getenv("HIVE_STATE_PATH", "data/hive_state.json"))
MEMPALACE_ENABLED = os.getenv("HIVE_MEMPALACE_ENABLED", "true").lower() == "true"
TOOL_PERMISSION_STATES = {"allow", "ask", "deny"}
DEFAULT_TOOL_PERMISSIONS = {
    "memory_read": "allow",
    "memory_write": "allow",
    "pulse": "allow",
    "openclaw_chat": "allow",
    "telegram_send": "allow",
    "brave_search": "ask",
    "gmail": "ask",
    "calendar": "ask",
    "notion": "ask",
    "todo": "allow",
    "notes": "allow",
    "filesystem": "deny",
    "browser": "deny",
    "shell": "deny",
}


class UnknownSession(KeyError):
    pass


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"sessions": {}, "agents": {}, "user_runtimes": {}}

    with STATE_PATH.open("r", encoding="utf-8") as handle:
        state = json.load(handle)

    state.setdefault("sessions", {})
    state.setdefault("agents", {})
    state.setdefault("user_runtimes", {})
    return state


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(state, indent=2, sort_keys=True, default=str)
    temp_path = STATE_PATH.with_suffix(f"{STATE_PATH.suffix}.tmp")
    temp_path.write_text(payload, encoding="utf-8")
    temp_path.replace(STATE_PATH)


def create_session(user_name: str) -> dict[str, Any]:
    raise RuntimeError("Legacy HIVE session creation is disabled. Create an agent instead.")


def public_agent(agent: dict[str, Any]) -> dict[str, Any]:
    safe = dict(agent)
    token = safe.pop("telegram_bot_token", None)
    safe["telegram_bot_configured"] = bool(token)
    safe["telegram_bot_id"] = token.split(":", maxsplit=1)[0] if token else ""
    safe["tool_permissions"] = normalize_tool_permissions(
        safe.get("tool_permissions")
    )
    return safe


def normalize_tool_permissions(
    permissions: dict[str, Any] | None,
) -> dict[str, str]:
    normalized = dict(DEFAULT_TOOL_PERMISSIONS)
    if not permissions:
        return normalized

    for tool_name, state in permissions.items():
        if tool_name not in DEFAULT_TOOL_PERMISSIONS:
            continue
        state_text = str(state).lower()
        if state_text in TOOL_PERMISSION_STATES:
            normalized[tool_name] = state_text
    return normalized


def create_agent(
    user_name: str,
    agent_name: str,
    agent_role: str,
    telegram_bot_token: str,
    user_id: str | None = None,
) -> dict[str, Any]:
    state = load_state()

    while True:
        agent_id = f"AGENT-{secrets.token_hex(4).upper()}"
        if agent_id not in state["agents"] and agent_id not in state["sessions"]:
            break

    timestamp = now_iso()
    agent = {
        "agent_id": agent_id,
        "user_id": user_id,
        "user_name": user_name,
        "agent_name": agent_name,
        "agent_role": agent_role,
        "agent_type": "agent",
        "parent_agent_id": None,
        "telegram_bot_token": telegram_bot_token,
        "telegram_chat_id": None,
        "openclaw_agent_id": None,
        "tool_permissions": dict(DEFAULT_TOOL_PERMISSIONS),
        "permission_audit": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    session = {
        "pairing_code": agent_id,
        "agent_id": agent_id,
        "user_id": user_id,
        "agent_name": agent_name,
        "agent_role": agent_role,
        "user_name": user_name,
        "telegram_chat_id": None,
        "goals": [],
        "dumps": [],
        "created_at": timestamp,
        "updated_at": timestamp,
    }

    state["agents"][agent_id] = agent
    state["sessions"][agent_id] = session
    save_state(state)
    return public_agent(agent)


def list_agents(user_id: str | None = None) -> list[dict[str, Any]]:
    state = load_state()
    agents = state["agents"].values()
    if user_id:
        agents = [
            agent for agent in agents if str(agent.get("user_id")) == str(user_id)
        ]
    return [public_agent(agent) for agent in agents]


def get_agent(agent_id: str, include_token: bool = False) -> dict[str, Any]:
    state = load_state()
    agent = state["agents"].get(agent_id)
    if agent is None:
        raise UnknownSession(agent_id)
    if include_token:
        return agent
    return public_agent(agent)


def get_agent_for_user(
    agent_id: str,
    user_id: str | None,
    include_token: bool = False,
) -> dict[str, Any]:
    agent = get_agent(agent_id, include_token=True)
    if user_id and str(agent.get("user_id")) != str(user_id):
        raise UnknownSession(agent_id)
    if include_token:
        return agent
    return public_agent(agent)


def get_agent_permissions(agent_id: str) -> dict[str, Any]:
    agent = get_agent(agent_id, include_token=True)
    permissions = normalize_tool_permissions(agent.get("tool_permissions"))
    return {
        "agent_id": agent_id,
        "tool_permissions": permissions,
        "available_tools": list(DEFAULT_TOOL_PERMISSIONS.keys()),
        "states": sorted(TOOL_PERMISSION_STATES),
        "audit": agent.get("permission_audit", [])[-25:],
    }


def update_agent_permissions(
    agent_id: str,
    updates: dict[str, str],
    changed_by: str = "system",
) -> dict[str, Any]:
    invalid_tools = [
        tool_name
        for tool_name in updates
        if tool_name not in DEFAULT_TOOL_PERMISSIONS
    ]
    if invalid_tools:
        raise ValueError(f"Unknown tool permission(s): {', '.join(invalid_tools)}")

    invalid_states = [
        state
        for state in updates.values()
        if str(state).lower() not in TOOL_PERMISSION_STATES
    ]
    if invalid_states:
        raise ValueError("Permission state must be one of: allow, ask, deny")

    state = load_state()
    agent = state["agents"].get(agent_id)
    if agent is None:
        raise UnknownSession(agent_id)

    permissions = normalize_tool_permissions(agent.get("tool_permissions"))
    timestamp = now_iso()
    audit = list(agent.get("permission_audit") or [])

    for tool_name, next_state in updates.items():
        previous_state = permissions.get(tool_name, DEFAULT_TOOL_PERMISSIONS[tool_name])
        next_state = str(next_state).lower()
        permissions[tool_name] = next_state
        if previous_state != next_state:
            audit.append(
                {
                    "tool": tool_name,
                    "from": previous_state,
                    "to": next_state,
                    "changed_by": changed_by,
                    "created_at": timestamp,
                }
            )

    agent["tool_permissions"] = permissions
    agent["permission_audit"] = audit[-100:]
    agent["updated_at"] = timestamp
    state["agents"][agent_id] = agent
    save_state(state)
    return get_agent_permissions(agent_id)


def reset_agent_permissions(agent_id: str, changed_by: str = "system") -> dict[str, Any]:
    return update_agent_permissions(
        agent_id,
        dict(DEFAULT_TOOL_PERMISSIONS),
        changed_by=changed_by,
    )


def get_tool_permission(agent_id: str, tool_name: str) -> str:
    if tool_name not in DEFAULT_TOOL_PERMISSIONS:
        raise ValueError(f"Unknown tool permission: {tool_name}")
    agent = get_agent(agent_id, include_token=True)
    permissions = normalize_tool_permissions(agent.get("tool_permissions"))
    return permissions[tool_name]


def is_tool_allowed(agent_id: str, tool_name: str) -> bool:
    return get_tool_permission(agent_id, tool_name) == "allow"


def get_agent_token(agent_id: str) -> str | None:
    agent = get_agent(agent_id, include_token=True)
    return agent.get("telegram_bot_token")


def get_user_runtime(user_id: str) -> dict[str, Any] | None:
    state = load_state()
    return state["user_runtimes"].get(user_id)


def list_user_runtimes() -> list[dict[str, Any]]:
    state = load_state()
    return list(state["user_runtimes"].values())


def upsert_user_runtime(user_id: str, runtime: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    existing = state["user_runtimes"].get(user_id, {})
    merged = {
        **existing,
        **runtime,
        "user_id": user_id,
        "updated_at": now_iso(),
    }
    if "created_at" not in merged:
        merged["created_at"] = merged["updated_at"]
    state["user_runtimes"][user_id] = merged
    save_state(state)
    return merged


def delete_user_runtime(user_id: str) -> dict[str, Any] | None:
    state = load_state()
    runtime = state["user_runtimes"].pop(user_id, None)
    save_state(state)
    return runtime


def delete_agent(agent_id: str) -> dict[str, Any]:
    state = load_state()
    agent = state["agents"].pop(agent_id, None)
    session = state["sessions"].pop(agent_id, None)
    if agent is None and session is None:
        raise UnknownSession(agent_id)

    save_state(state)
    return {
        "agent_id": agent_id,
        "agent_deleted": agent is not None,
        "session_deleted": session is not None,
    }


def sync_agent_chat_id(agent_id: str, chat_id: str | None) -> None:
    state = load_state()
    agent = state["agents"].get(agent_id)
    if agent is None:
        return
    agent["telegram_chat_id"] = chat_id
    agent["updated_at"] = now_iso()
    state["agents"][agent_id] = agent
    save_state(state)


def get_session(pairing_code: str) -> dict[str, Any]:
    state = load_state()
    session = state["sessions"].get(pairing_code)
    if session is None:
        raise UnknownSession(pairing_code)
    return session


def update_session(pairing_code: str, updates: dict[str, Any]) -> dict[str, Any]:
    state = load_state()
    session = state["sessions"].get(pairing_code)
    if session is None:
        raise UnknownSession(pairing_code)

    session.update(updates)
    session["updated_at"] = now_iso()
    state["sessions"][pairing_code] = session
    save_state(state)
    return session


def pair_telegram(pairing_code: str, chat_id: str) -> dict[str, Any]:
    state = load_state()
    if pairing_code not in state["sessions"]:
        raise UnknownSession(pairing_code)

    for code, session in state["sessions"].items():
        if code != pairing_code and str(session.get("telegram_chat_id")) == str(chat_id):
            session["telegram_chat_id"] = None
            session["telegram_awaiting_goal"] = False
            session["updated_at"] = now_iso()
            if session.get("agent_id") in state["agents"]:
                agent = state["agents"][session["agent_id"]]
                agent["telegram_chat_id"] = None
                agent["updated_at"] = now_iso()
                state["agents"][session["agent_id"]] = agent

    session = state["sessions"][pairing_code]
    session["telegram_chat_id"] = chat_id
    session["updated_at"] = now_iso()
    state["sessions"][pairing_code] = session
    if session.get("agent_id") in state["agents"]:
        agent = state["agents"][session["agent_id"]]
        agent["telegram_chat_id"] = chat_id
        agent["updated_at"] = now_iso()
        state["agents"][session["agent_id"]] = agent
    save_state(state)
    return session


def activate_telegram_session(pairing_code: str) -> dict[str, Any]:
    session = get_session(pairing_code)
    chat_id = session.get("telegram_chat_id")
    if not chat_id:
        raise ValueError("Session has no Telegram chat id")
    return pair_telegram(pairing_code, str(chat_id))


def add_goal(pairing_code: str, goal_text: str) -> dict[str, Any]:
    session = get_session(pairing_code)
    goal = {"text": goal_text, "created_at": now_iso()}
    update_session(pairing_code, {"goals": [*session["goals"], goal]})
    mirror_goal(pairing_code, goal)
    return goal


def ingest_dump(
    pairing_code: str,
    title: str,
    text: str,
    source_url: str | None = None,
) -> dict[str, Any]:
    session = get_session(pairing_code)
    dump = {
        "title": title,
        "text": text,
        "source_url": source_url,
        "created_at": now_iso(),
    }
    update_session(pairing_code, {"dumps": [*session["dumps"], dump]})
    mirror_dump(pairing_code, dump)
    return dump


def get_context(pairing_code: str) -> dict[str, Any]:
    session = get_session(pairing_code)
    context = {
        "pairing_code": pairing_code,
        "agent_id": session.get("agent_id", pairing_code),
        "user_id": session.get("user_id"),
        "user_name": session["user_name"],
        "agent_name": session.get("agent_name"),
        "agent_role": session.get("agent_role"),
        "telegram_paired": session["telegram_chat_id"] is not None,
        "goals": session["goals"],
        "dumps": session["dumps"],
    }
    if MEMPALACE_ENABLED:
        context["mempalace"] = mempalace_memory.list_session_memory(pairing_code)
    return context


def find_pairing_code_for_chat(chat_id: str) -> str | None:
    state = load_state()
    for pairing_code, session in state["sessions"].items():
        if str(session.get("telegram_chat_id")) == chat_id:
            return pairing_code
    return None


def set_awaiting_goal(pairing_code: str, awaiting: bool) -> dict[str, Any]:
    return update_session(pairing_code, {"telegram_awaiting_goal": awaiting})


def get_pulse_status() -> dict[str, int]:
    state = load_state()
    sessions = {
        code: session
        for code, session in state["sessions"].items()
        if session.get("agent_id")
    }
    paired_sessions = [
        session for session in sessions.values() if session.get("telegram_chat_id")
    ]
    pulse_ready_sessions = [
        session
        for session in paired_sessions
        if session.get("goals") and not session.get("telegram_awaiting_goal")
    ]
    return {
        "total_sessions": len(sessions),
        "paired_sessions": len(paired_sessions),
        "pulse_ready_sessions": len(pulse_ready_sessions),
    }


def list_pulse_candidates() -> list[tuple[str, dict[str, Any]]]:
    state = load_state()
    candidates = []
    for pairing_code, session in state["sessions"].items():
        if not session.get("agent_id"):
            continue
        if not session.get("telegram_chat_id"):
            continue
        if not session.get("goals"):
            continue
        if session.get("telegram_awaiting_goal"):
            continue
        candidates.append((pairing_code, session))
    return candidates


def mark_pulse_sent(pairing_code: str, delivery: str) -> dict[str, Any]:
    return update_session(
        pairing_code,
        {
            "last_pulse_sent_at": now_iso(),
            "last_pulse_delivery": delivery,
        },
    )


def mirror_goal(pairing_code: str, goal: dict[str, Any]) -> None:
    if not MEMPALACE_ENABLED:
        return

    try:
        drawer_id = mempalace_memory.store_goal(pairing_code, goal)
        update_session(pairing_code, {"last_mempalace_goal_drawer_id": drawer_id})
    except Exception as exc:
        update_session(pairing_code, {"last_mempalace_error": str(exc)})


def mirror_dump(pairing_code: str, dump: dict[str, Any]) -> None:
    if not MEMPALACE_ENABLED:
        return

    try:
        drawer_id = mempalace_memory.store_dump(pairing_code, dump)
        update_session(pairing_code, {"last_mempalace_dump_drawer_id": drawer_id})
    except Exception as exc:
        update_session(pairing_code, {"last_mempalace_error": str(exc)})


def search_memory(pairing_code: str, query: str, n_results: int = 5) -> dict[str, Any]:
    get_session(pairing_code)
    if not MEMPALACE_ENABLED:
        return {"error": "MemPalace integration is disabled"}
    return mempalace_memory.search_session_memory(pairing_code, query, n_results)


def get_mempalace_status() -> dict[str, Any]:
    if not MEMPALACE_ENABLED:
        return {"enabled": False}
    return mempalace_memory.status()


def backfill_session_to_mempalace(pairing_code: str) -> dict[str, Any]:
    session = get_session(pairing_code)
    if not MEMPALACE_ENABLED:
        return {
            "pairing_code": pairing_code,
            "enabled": False,
            "goals_backfilled": 0,
            "dumps_backfilled": 0,
        }

    goal_ids = []
    dump_ids = []
    errors = []

    for goal in session.get("goals", []):
        try:
            goal_ids.append(mempalace_memory.store_goal(pairing_code, goal))
        except Exception as exc:
            errors.append(str(exc))

    for dump in session.get("dumps", []):
        try:
            dump_ids.append(mempalace_memory.store_dump(pairing_code, dump))
        except Exception as exc:
            errors.append(str(exc))

    updates = {
        "last_mempalace_backfill_at": now_iso(),
        "last_mempalace_backfill_goal_count": len(goal_ids),
        "last_mempalace_backfill_dump_count": len(dump_ids),
    }
    if errors:
        updates["last_mempalace_error"] = "; ".join(errors[:3])
    update_session(pairing_code, updates)

    return {
        "pairing_code": pairing_code,
        "enabled": True,
        "goals_backfilled": len(goal_ids),
        "dumps_backfilled": len(dump_ids),
        "errors": errors,
    }
