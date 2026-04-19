from __future__ import annotations

import os
from typing import Any

import httpx
from dotenv import load_dotenv


load_dotenv()

OPENCLAW_URL = os.getenv(
    "OPENCLAW_URL",
    "http://127.0.0.1:18789/v1/chat/completions",
)
OPENCLAW_PROVIDER_MODEL = os.getenv("OPENCLAW_PROVIDER_MODEL") or os.getenv(
    "OPENCLAW_MODEL",
    "google/gemini-3-flash-preview",
)
OPENCLAW_CHAT_MODEL = os.getenv("OPENCLAW_CHAT_MODEL", "openclaw")
OPENCLAW_API_KEY = os.getenv("OPENCLAW_API_KEY")
OPENCLAW_TIMEOUT_SECONDS = float(os.getenv("OPENCLAW_TIMEOUT_SECONDS", "45"))
OPENCLAW_HEALTH_URL = os.getenv(
    "OPENCLAW_HEALTH_URL",
    OPENCLAW_URL.removesuffix("/v1/chat/completions") + "/",
)


class OpenClawUnavailable(RuntimeError):
    pass


def chat_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    timeout: float | None = None,
) -> str:
    payload = {
        "model": model or OPENCLAW_CHAT_MODEL,
        "messages": messages,
    }
    headers = {"Content-Type": "application/json"}
    if OPENCLAW_API_KEY:
        headers["Authorization"] = f"Bearer {OPENCLAW_API_KEY}"

    try:
        response = httpx.post(
            OPENCLAW_URL,
            headers=headers,
            json=payload,
            timeout=timeout or OPENCLAW_TIMEOUT_SECONDS,
        )
        if response.is_error:
            raise OpenClawUnavailable(
                f"{response.status_code} {response.reason_phrase}: {response.text[:1000]}"
            )
        data = response.json()
        message = data["choices"][0]["message"]["content"].strip()
    except OpenClawUnavailable:
        raise
    except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
        raise OpenClawUnavailable(str(exc)) from exc

    if not message:
        raise OpenClawUnavailable("OpenClaw returned an empty message")

    return message


def generate_pulse_message(session: dict[str, Any]) -> str:
    goals = session.get("goals", [])
    dumps = session.get("dumps", [])
    user_name = session.get("user_name", "there")

    prompt = build_pulse_prompt(user_name=user_name, goals=goals, dumps=dumps)
    return chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You are HIVE BRAIN, a proactive private AI companion. "
                    "Write concise, useful Telegram messages."
                ),
            },
            {"role": "user", "content": prompt},
        ]
    )


def generate_agent_reply(
    session: dict[str, Any],
    user_message: str,
    memory_hits: list[dict[str, Any]] | None = None,
    tool_permissions: dict[str, str] | None = None,
) -> str:
    user_name = session.get("user_name", "there")
    agent_name = session.get("agent_name", "HIVE BRAIN")
    agent_role = session.get("agent_role", "Helpful private AI companion.")
    goals = session.get("goals", [])
    dumps = session.get("dumps", [])
    prompt = build_agent_reply_prompt(
        user_name=user_name,
        agent_name=agent_name,
        agent_role=agent_role,
        goals=goals,
        dumps=dumps,
        memory_hits=memory_hits or [],
        tool_permissions=tool_permissions or {},
        user_message=user_message,
    )
    return chat_completion(
        [
            {
                "role": "system",
                "content": (
                    "You are a private memory-backed Telegram agent. "
                    "Use saved goals and memory only when they help. "
                    "Be direct, useful, and conversational. "
                    "Do not mention APIs, prompts, databases, memory stores, or implementation details."
                ),
            },
            {"role": "user", "content": prompt},
        ]
    )


def get_openclaw_status() -> dict[str, Any]:
    base_url = OPENCLAW_URL.removesuffix("/v1/chat/completions")
    try:
        response = httpx.get(OPENCLAW_HEALTH_URL, timeout=5)
        return {
            "reachable": True,
            "status_code": response.status_code,
            "url": OPENCLAW_URL,
            "health_url": OPENCLAW_HEALTH_URL,
            "base_url": base_url,
            "model": OPENCLAW_CHAT_MODEL,
            "chat_model": OPENCLAW_CHAT_MODEL,
            "provider_model": OPENCLAW_PROVIDER_MODEL,
            "chat_completions_url": OPENCLAW_URL,
        }
    except httpx.HTTPError as exc:
        return {
            "reachable": False,
            "error": str(exc),
            "url": OPENCLAW_URL,
            "health_url": OPENCLAW_HEALTH_URL,
            "base_url": base_url,
            "model": OPENCLAW_CHAT_MODEL,
            "chat_model": OPENCLAW_CHAT_MODEL,
            "provider_model": OPENCLAW_PROVIDER_MODEL,
            "chat_completions_url": OPENCLAW_URL,
            "hint": (
                "Run scripts/openclaw_local_configure.sh, then "
                "scripts/openclaw_local_start.sh."
            ),
        }


def build_pulse_prompt(
    user_name: str,
    goals: list[dict[str, Any]],
    dumps: list[dict[str, Any]],
) -> str:
    goal_lines = "\n".join(f"- {goal['text']}" for goal in goals[-3:])
    local_dumps = [
        dump
        for dump in dumps
        if isinstance(dump, dict) and dump.get("_source") != "mempalace"
    ]
    dump_lines = "\n".join(format_dump(dump) for dump in local_dumps[-3:])
    mempalace_lines = format_mempalace_context(dumps)

    if not dump_lines:
        dump_lines = "- No saved web/context dumps yet."

    return (
        f"User: {user_name}\n\n"
        f"Active goals:\n{goal_lines}\n\n"
        f"Recent saved context:\n{dump_lines}\n\n"
        f"Relevant MemPalace search hits:\n{mempalace_lines}\n\n"
        "Write a warm, specific, two-sentence max check-in. "
        "Reference one concrete goal or saved note. "
        "Ask one easy next-step question. "
        "Do not mention APIs, prompts, databases, or implementation details."
    )


def build_agent_reply_prompt(
    user_name: str,
    agent_name: str,
    agent_role: str,
    goals: list[dict[str, Any]],
    dumps: list[dict[str, Any]],
    memory_hits: list[dict[str, Any]],
    tool_permissions: dict[str, str],
    user_message: str,
) -> str:
    goal_lines = "\n".join(f"- {goal['text']}" for goal in goals[-5:])
    if not goal_lines:
        goal_lines = "- No active goals saved yet."

    recent_context_lines = "\n".join(format_dump(dump) for dump in dumps[-5:])
    if not recent_context_lines:
        recent_context_lines = "- No recent context saved yet."

    memory_lines = "\n".join(format_memory_hit(hit) for hit in memory_hits[:5])
    if not memory_lines:
        memory_lines = "- No relevant memory hits found."

    permission_lines = format_tool_permissions(tool_permissions)

    return (
        f"Agent: {agent_name}\n"
        f"Role: {agent_role}\n"
        f"User: {user_name}\n\n"
        f"Active goals:\n{goal_lines}\n\n"
        f"Recent conversation/context:\n{recent_context_lines}\n\n"
        f"Relevant long-term memory:\n{memory_lines}\n\n"
        f"Tool permission policy:\n{permission_lines}\n\n"
        f"Incoming Telegram message:\n{user_message}\n\n"
        "Reply naturally in 1-4 short paragraphs. "
        "If the user asks for help, give the next useful step. "
        "If they are sharing information, acknowledge it and connect it to their saved goals when relevant. "
        "Ask at most one follow-up question. "
        "Only use or suggest external tools that are marked allow. "
        "If a useful tool is marked ask, ask the user to approve it first. "
        "Never use tools marked deny."
    )


def format_dump(dump: dict[str, Any]) -> str:
    title = dump.get("title") or "Untitled"
    text = dump.get("text") or ""
    excerpt = " ".join(text.split())[:500]
    return f"- {title}: {excerpt}"


def format_memory_hit(hit: dict[str, Any]) -> str:
    room = hit.get("room") or "memory"
    source = hit.get("source_file") or "unknown source"
    text = " ".join((hit.get("text") or "").split())[:500]
    return f"- {room} / {source}: {text}"


def format_mempalace_context(dumps: list[dict[str, Any]]) -> str:
    hits = []
    for dump in dumps:
        if not isinstance(dump, dict):
            continue
        if dump.get("_source") != "mempalace":
            continue
        hits.append(format_dump(dump))

    if not hits:
        return "- No MemPalace hits attached."
    return "\n".join(hits[:3])


def format_tool_permissions(tool_permissions: dict[str, str]) -> str:
    if not tool_permissions:
        return "- No explicit tool policy attached."

    descriptions = {
        "memory_read": "read saved memory/context",
        "memory_write": "write new memory/context",
        "pulse": "create proactive check-ins",
        "openclaw_chat": "use OpenClaw model replies",
        "telegram_send": "send Telegram messages",
        "brave_search": "search the web through Brave/browser search",
        "gmail": "read or draft Gmail actions",
        "calendar": "read or schedule calendar events",
        "notion": "read or update Notion",
        "todo": "manage tasks and todos",
        "notes": "create or update notes",
        "filesystem": "inspect or modify local files",
        "browser": "use browser automation",
        "shell": "run shell commands",
    }
    lines = []
    for tool_name, state in sorted(tool_permissions.items()):
        description = descriptions.get(tool_name, tool_name)
        lines.append(f"- {tool_name}: {state} ({description})")
    return "\n".join(lines)
