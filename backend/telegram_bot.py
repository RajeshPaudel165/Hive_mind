from __future__ import annotations

import os
import time
from typing import Any

import httpx
from dotenv import load_dotenv

import main
import memory_store
import openclaw_manager
from openclaw_client import OpenClawUnavailable, generate_agent_reply


load_dotenv()

ACTIVE_AGENT_ID = os.getenv("HIVE_AGENT_ID")
TELEGRAM_API_BASE = os.getenv("TELEGRAM_API_BASE", "https://api.telegram.org")
POLL_TIMEOUT_SECONDS = int(os.getenv("TELEGRAM_POLL_TIMEOUT_SECONDS", "30"))
SAVE_ASSISTANT_REPLIES = (
    os.getenv("HIVE_SAVE_ASSISTANT_REPLIES", "true").lower() == "true"
)


class TelegramConfigError(RuntimeError):
    pass


def get_bot_token() -> str | None:
    if ACTIVE_AGENT_ID:
        return memory_store.get_agent_token(ACTIVE_AGENT_ID)
    return None


def telegram_api_url(method: str) -> str:
    bot_token = get_bot_token()
    if not bot_token:
        raise TelegramConfigError("Missing HIVE_AGENT_ID or agent Telegram bot token")
    return f"{TELEGRAM_API_BASE}/bot{bot_token}/{method}"


def send_message(chat_id: str | int, text: str) -> None:
    response = httpx.post(
        telegram_api_url("sendMessage"),
        json={"chat_id": chat_id, "text": text},
        timeout=15,
    )
    response.raise_for_status()


def get_updates(offset: int | None) -> list[dict[str, Any]]:
    params: dict[str, Any] = {"timeout": POLL_TIMEOUT_SECONDS}
    if offset is not None:
        params["offset"] = offset

    response = httpx.get(telegram_api_url("getUpdates"), params=params, timeout=40)
    response.raise_for_status()
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"Telegram getUpdates failed: {data}")
    return data.get("result", [])


def find_pairing_code_for_chat(chat_id: str) -> str | None:
    if ACTIVE_AGENT_ID:
        try:
            session = memory_store.get_session(ACTIVE_AGENT_ID)
        except memory_store.UnknownSession:
            return None
        if str(session.get("telegram_chat_id")) == chat_id:
            return ACTIVE_AGENT_ID
        return None
    return memory_store.find_pairing_code_for_chat(chat_id)


def mark_awaiting_goal(pairing_code: str, awaiting: bool) -> None:
    memory_store.set_awaiting_goal(pairing_code, awaiting)


def command_body(text: str, command: str) -> str:
    if text == command:
        return ""
    return text.removeprefix(f"{command} ").strip()


def handle_text(chat_id: str, text: str) -> str:
    clean_text = text.strip()
    if clean_text.startswith("/start"):
        return handle_start(chat_id, clean_text)

    pairing_code = find_pairing_code_for_chat(chat_id)
    if pairing_code is None:
        return "Send /start to connect this bot to its agent."

    if clean_text == "/goal" or clean_text.startswith("/goal "):
        goal_text = command_body(clean_text, "/goal")
        if not goal_text:
            return "Send /goal followed by the goal you want me to remember."
        main.add_goal(pairing_code, main.GoalInput(goal=goal_text))
        return "Got it. I saved that as your active goal."

    if clean_text == "/save" or clean_text.startswith("/save "):
        return handle_save(pairing_code, command_body(clean_text, "/save"))

    if clean_text == "/recall" or clean_text.startswith("/recall "):
        return handle_recall(pairing_code, command_body(clean_text, "/recall"))

    if clean_text == "/pulse":
        pulse = main.create_pulse_preview(pairing_code)
        return pulse["message"]

    session = main.get_session_or_404(pairing_code)
    if session.get("telegram_awaiting_goal"):
        main.add_goal(pairing_code, main.GoalInput(goal=clean_text))
        mark_awaiting_goal(pairing_code, False)
        return "Saved as your active goal. Send me notes anytime and I will remember them."

    return handle_agent_message(pairing_code, clean_text)


def handle_agent_message(pairing_code: str, clean_text: str) -> str:
    main.ingest_dump(
        pairing_code,
        main.IngestInput(title="Telegram message", text=clean_text),
    )
    session = main.get_session_or_404(pairing_code)
    memory_hits = search_relevant_memory(pairing_code, clean_text)
    openclaw_manager.ensure_running()

    try:
        reply = generate_agent_reply(
            session=session,
            user_message=clean_text,
            memory_hits=memory_hits,
        )
    except OpenClawUnavailable as exc:
        return (
            "Saved that to your Hive Brain, but I could not generate a reply yet: "
            f"{exc}"
        )

    if SAVE_ASSISTANT_REPLIES:
        main.ingest_dump(
            pairing_code,
            main.IngestInput(title="Assistant reply", text=reply),
        )

    return reply


def search_relevant_memory(pairing_code: str, query: str) -> list[dict[str, Any]]:
    try:
        results = memory_store.search_memory(pairing_code, query=query, n_results=5)
    except Exception:
        return []
    if results.get("error"):
        return []
    return results.get("results") or []


def handle_start(chat_id: str, text: str) -> str:
    parts = text.split(maxsplit=1)
    if ACTIVE_AGENT_ID and len(parts) == 1:
        main.pair_telegram(ACTIVE_AGENT_ID, main.PairTelegram(chat_id=chat_id))
        mark_awaiting_goal(ACTIVE_AGENT_ID, True)
        return "Your Hive Brain is connected. What is your primary goal right now?"

    if not ACTIVE_AGENT_ID:
        return "This bot is not assigned to an agent yet. Start it with HIVE_AGENT_ID."

    return "Send /start without extra text to connect this bot."


def handle_save(pairing_code: str, body: str) -> str:
    if not body:
        return "Send /save followed by the note you want me to remember."

    title = "Telegram note"
    text = body
    if "|" in body:
        raw_title, raw_text = body.split("|", maxsplit=1)
        title = raw_title.strip() or title
        text = raw_text.strip()

    if not text:
        return "Send /save followed by the note you want me to remember."

    main.ingest_dump(pairing_code, main.IngestInput(title=title, text=text))
    return "Saved that context."


def handle_recall(pairing_code: str, query: str) -> str:
    if not query:
        return "Send /recall followed by what you want me to search for."

    results = main.search_memory(
        pairing_code,
        main.MemorySearchInput(query=query, n_results=3),
    )
    if results.get("error"):
        return f"I could not search memory yet: {results['error']}"

    hits = results.get("results") or []
    if not hits:
        return "I could not find a matching memory yet."

    lines = [f"I found {len(hits)} memory match(es):"]
    for index, hit in enumerate(hits, 1):
        source = hit.get("source_file", "memory")
        room = hit.get("room", "context")
        text = " ".join((hit.get("text") or "").split())
        if len(text) > 260:
            text = text[:257] + "..."
        lines.append(f"{index}. {room} / {source}\n{text}")

    return "\n\n".join(lines)


def handle_update(update: dict[str, Any]) -> None:
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text = message.get("text")

    if chat_id is None or not text:
        return

    try:
        reply = handle_text(str(chat_id), text)
    except Exception as exc:
        reply = f"I could not process that yet: {exc}"

    send_message(chat_id, reply)


def run_polling() -> None:
    if not get_bot_token():
        raise TelegramConfigError(
            "Set HIVE_AGENT_ID for an agent with a Telegram bot token"
        )

    offset = None
    if ACTIVE_AGENT_ID:
        print(f"Telegram long polling started for {ACTIVE_AGENT_ID}.")
    else:
        print("Telegram long polling started.")
    while True:
        try:
            updates = get_updates(offset)
            for update in updates:
                offset = update["update_id"] + 1
                handle_update(update)
        except KeyboardInterrupt:
            print("Telegram long polling stopped.")
            return
        except Exception as exc:
            print(f"Telegram polling error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    run_polling()
