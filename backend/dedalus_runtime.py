from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

import memory_store


load_dotenv()

RUNTIME_MODE = os.getenv("HIVE_RUNTIME_MODE", "local").lower()
DEDALUS_MACHINE_VCPU = int(os.getenv("DEDALUS_MACHINE_VCPU", "1"))
DEDALUS_MACHINE_MEMORY_MIB = int(os.getenv("DEDALUS_MACHINE_MEMORY_MIB", "2048"))
DEDALUS_MACHINE_STORAGE_GIB = int(os.getenv("DEDALUS_MACHINE_STORAGE_GIB", "10"))
DEDALUS_ORG_ID = os.getenv("DEDALUS_ORG_ID")
DEDALUS_API_KEY = os.getenv("DEDALUS_API_KEY")


class DedalusRuntimeError(RuntimeError):
    pass


def runtime_enabled() -> bool:
    return RUNTIME_MODE == "dedalus"


def get_runtime_status(user_id: str) -> dict[str, Any]:
    runtime = memory_store.get_user_runtime(user_id)
    if not runtime:
        return {
            "user_id": user_id,
            "mode": RUNTIME_MODE,
            "exists": False,
            "ready": False,
            "message": "No runtime has been provisioned for this user.",
        }

    if runtime.get("provider") != "dedalus" or not runtime.get("machine_id"):
        return {
            **runtime,
            "mode": RUNTIME_MODE,
            "exists": True,
            "ready": runtime.get("status") in {"local", "stub", "running", "ready"},
        }

    remote_status = fetch_machine_status(runtime["machine_id"])
    if remote_status.get("ok"):
        runtime = memory_store.upsert_user_runtime(
            user_id,
            {
                **runtime,
                "status": remote_status.get("status") or runtime.get("status"),
                "machine": remote_status.get("machine"),
                "last_status_error": None,
            },
        )
    else:
        runtime = memory_store.upsert_user_runtime(
            user_id,
            {
                **runtime,
                "last_status_error": remote_status.get("error"),
            },
        )

    return {
        **runtime,
        "mode": RUNTIME_MODE,
        "exists": True,
        "ready": runtime.get("status") in {"running", "ready"},
    }


def ensure_user_runtime(user_id: str) -> dict[str, Any]:
    existing = memory_store.get_user_runtime(user_id)
    if existing:
        status = get_runtime_status(user_id)
        if status.get("ready") or status.get("machine_id"):
            return {
                **status,
                "created": False,
                "message": "User runtime already exists.",
            }

    if not runtime_enabled():
        runtime = memory_store.upsert_user_runtime(
            user_id,
            {
                "provider": "local",
                "status": "local",
                "machine_id": None,
                "machine": None,
                "runtime_url": "http://127.0.0.1:8010",
            },
        )
        return {
            **runtime,
            "mode": RUNTIME_MODE,
            "exists": True,
            "ready": True,
            "created": False,
            "message": "Local runtime mode is active.",
        }

    machine = create_dedalus_machine()
    runtime = memory_store.upsert_user_runtime(
        user_id,
        {
            "provider": "dedalus",
            "status": machine.get("status", "provisioned"),
            "machine_id": machine.get("machine_id"),
            "machine": machine,
            "runtime_url": None,
            "bootstrap_status": "pending",
            "spec": {
                "vcpu": DEDALUS_MACHINE_VCPU,
                "memory_mib": DEDALUS_MACHINE_MEMORY_MIB,
                "storage_gib": DEDALUS_MACHINE_STORAGE_GIB,
            },
        },
    )
    return {
        **runtime,
        "mode": RUNTIME_MODE,
        "exists": True,
        "ready": runtime.get("status") in {"running", "ready"},
        "created": True,
        "message": "Dedalus runtime provisioned. Bootstrap is the next step.",
    }


def destroy_user_runtime(user_id: str) -> dict[str, Any]:
    runtime = memory_store.get_user_runtime(user_id)
    if not runtime:
        return {
            "user_id": user_id,
            "deleted": False,
            "message": "No runtime existed for this user.",
        }

    machine_id = runtime.get("machine_id")
    destroy_result = None
    if runtime.get("provider") == "dedalus" and machine_id:
        destroy_result = destroy_dedalus_machine(machine_id)

    memory_store.delete_user_runtime(user_id)
    return {
        "user_id": user_id,
        "deleted": True,
        "machine_id": machine_id,
        "destroy_result": destroy_result,
    }


def create_dedalus_machine() -> dict[str, Any]:
    if not DEDALUS_API_KEY:
        return {
            "machine_id": f"stub-{memory_store.now_iso()}",
            "status": "stub",
            "stub": True,
            "error": "DEDALUS_API_KEY is not set; recorded a stub runtime.",
        }

    try:
        from dedalus_sdk import Dedalus
    except ImportError as exc:
        raise DedalusRuntimeError(
            "Install dedalus-sdk in the backend venv before real machine provisioning."
        ) from exc

    client_kwargs: dict[str, Any] = {"api_key": DEDALUS_API_KEY}
    if DEDALUS_ORG_ID:
        client_kwargs["default_headers"] = {"X-Dedalus-Org-Id": DEDALUS_ORG_ID}

    client = Dedalus(**client_kwargs)
    machine = client.machines.create(
        vcpu=DEDALUS_MACHINE_VCPU,
        memory_mib=DEDALUS_MACHINE_MEMORY_MIB,
        storage_gib=DEDALUS_MACHINE_STORAGE_GIB,
    )
    return model_to_dict(machine)


def fetch_machine_status(machine_id: str) -> dict[str, Any]:
    if machine_id.startswith("stub-"):
        return {"ok": True, "status": "stub", "machine": {"machine_id": machine_id}}
    if not DEDALUS_API_KEY:
        return {"ok": False, "error": "DEDALUS_API_KEY is not set."}

    try:
        from dedalus_sdk import Dedalus
    except ImportError as exc:
        return {"ok": False, "error": f"dedalus-sdk is not installed: {exc}"}

    try:
        client = Dedalus(api_key=DEDALUS_API_KEY)
        machine = client.machines.retrieve(machine_id=machine_id)
        data = model_to_dict(machine)
        return {
            "ok": True,
            "status": data.get("status"),
            "machine": data,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def destroy_dedalus_machine(machine_id: str) -> dict[str, Any]:
    if machine_id.startswith("stub-"):
        return {"ok": True, "stub": True, "machine_id": machine_id}
    if not DEDALUS_API_KEY:
        return {"ok": False, "error": "DEDALUS_API_KEY is not set."}

    try:
        from dedalus_sdk import Dedalus
    except ImportError as exc:
        return {"ok": False, "error": f"dedalus-sdk is not installed: {exc}"}

    try:
        client = Dedalus(api_key=DEDALUS_API_KEY)
        result = client.machines.delete(machine_id=machine_id)
        return {"ok": True, "result": model_to_dict(result)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def model_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, dict):
        return value
    return {"value": str(value)}
