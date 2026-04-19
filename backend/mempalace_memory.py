from __future__ import annotations

import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from mempalace.palace import NORMALIZE_VERSION, get_collection
from mempalace.searcher import search_memories


load_dotenv()

BACKEND_DIR = Path(__file__).resolve().parent


def resolve_backend_path(value: str) -> str:
    path = Path(value)
    if path.is_absolute():
        return str(path)
    return str(BACKEND_DIR / path)


MEMPALACE_PATH = resolve_backend_path(os.getenv("HIVE_MEMPALACE_PATH", "data/mempalace"))
MEMPALACE_AGENT = os.getenv("HIVE_MEMPALACE_AGENT", "hive_brain")


def now_iso() -> str:
    return datetime.now(UTC).isoformat()


def wing_for_pairing_code(pairing_code: str) -> str:
    return f"hive_{pairing_code.lower().replace('-', '_')}"


def stable_drawer_id(
    pairing_code: str,
    room: str,
    content: str,
    created_at: str,
) -> str:
    digest = hashlib.sha256(
        f"{pairing_code}|{room}|{created_at}|{content}".encode("utf-8")
    ).hexdigest()[:24]
    return f"drawer_{wing_for_pairing_code(pairing_code)}_{room}_{digest}"


def upsert_memory(
    pairing_code: str,
    room: str,
    content: str,
    title: str,
    source_url: str | None = None,
    created_at: str | None = None,
) -> str:
    created_at = created_at or now_iso()
    wing = wing_for_pairing_code(pairing_code)
    source_file = source_url or f"telegram:{pairing_code}:{room}:{title}"
    drawer_id = stable_drawer_id(pairing_code, room, content, created_at)
    metadata = {
        "wing": wing,
        "room": room,
        "source_file": source_file,
        "source_title": title,
        "chunk_index": 0,
        "added_by": MEMPALACE_AGENT,
        "filed_at": created_at,
        "normalize_version": NORMALIZE_VERSION,
        "hall": "hive_brain",
        "pairing_code": pairing_code,
    }

    collection = get_collection(MEMPALACE_PATH, create=True)
    collection.upsert(
        documents=[content],
        ids=[drawer_id],
        metadatas=[metadata],
    )
    return drawer_id


def store_goal(pairing_code: str, goal: dict[str, Any]) -> str:
    return upsert_memory(
        pairing_code=pairing_code,
        room="goals",
        content=goal["text"],
        title="Active goal",
        created_at=goal.get("created_at"),
    )


def store_dump(pairing_code: str, dump: dict[str, Any]) -> str:
    return upsert_memory(
        pairing_code=pairing_code,
        room="context",
        content=dump["text"],
        title=dump.get("title") or "Telegram note",
        source_url=dump.get("source_url"),
        created_at=dump.get("created_at"),
    )


def search_session_memory(
    pairing_code: str,
    query: str,
    n_results: int = 5,
) -> dict[str, Any]:
    return search_memories(
        query=query,
        palace_path=MEMPALACE_PATH,
        wing=wing_for_pairing_code(pairing_code),
        n_results=n_results,
    )


def list_session_memory(pairing_code: str, limit: int = 20) -> dict[str, Any]:
    wing = wing_for_pairing_code(pairing_code)
    try:
        collection = get_collection(MEMPALACE_PATH, create=False)
        data = collection.get(
            where={"wing": wing},
            include=["documents", "metadatas"],
        )
    except Exception as exc:
        return {"error": str(exc), "results": []}

    rows = []
    for drawer_id, text, meta in zip(
        data.get("ids") or [],
        data.get("documents") or [],
        data.get("metadatas") or [],
    ):
        rows.append(
            {
                "id": drawer_id,
                "text": text,
                "room": meta.get("room", "unknown"),
                "source_file": meta.get("source_file", "unknown"),
                "created_at": meta.get("filed_at", "unknown"),
            }
        )

    rows.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return {
        "wing": wing,
        "count": len(rows),
        "results": rows[:limit],
    }


def status() -> dict[str, Any]:
    try:
        collection = get_collection(MEMPALACE_PATH, create=False)
        return {
            "enabled": True,
            "reachable": True,
            "palace_path": MEMPALACE_PATH,
            "drawer_count": collection.count(),
        }
    except Exception as exc:
        return {
            "enabled": True,
            "reachable": False,
            "palace_path": MEMPALACE_PATH,
            "error": str(exc),
        }
