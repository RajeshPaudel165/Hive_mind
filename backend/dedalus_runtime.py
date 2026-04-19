from __future__ import annotations

import os
import time
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
DEDALUS_BOOTSTRAP_TIMEOUT_MS = int(
    os.getenv("DEDALUS_BOOTSTRAP_TIMEOUT_MS", "1800000")
)
DEDALUS_BOOTSTRAP_PREVIEW_VISIBILITY = os.getenv(
    "DEDALUS_BOOTSTRAP_PREVIEW_VISIBILITY", "private"
)
HIVE_REPO_URL = os.getenv("HIVE_REPO_URL", "")
HIVE_REMOTE_APP_DIR = os.getenv("HIVE_REMOTE_APP_DIR", "/home/machine/hive-brain")
HIVE_BACKEND_SUBDIR = os.getenv("HIVE_BACKEND_SUBDIR", "backend")
DEDALUS_HOME = os.getenv("DEDALUS_HOME", "/home/machine")


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
        status_value = normalize_machine_status(runtime.get("status"))
        return {
            **runtime,
            "mode": RUNTIME_MODE,
            "exists": True,
            "status": status_value,
            "ready": status_value in {"local", "stub", "running", "ready"},
        }

    remote_status = fetch_machine_status(runtime["machine_id"])
    if remote_status.get("ok"):
        runtime = memory_store.upsert_user_runtime(
            user_id,
            {
                **runtime,
                "status": normalize_machine_status(
                    remote_status.get("status") or runtime.get("status")
                ),
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

    status_value = normalize_machine_status(runtime.get("status"))
    return {
        **runtime,
        "mode": RUNTIME_MODE,
        "exists": True,
        "status": status_value,
        "ready": status_value in {"running", "ready", "stub"},
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
            "status": normalize_machine_status(machine.get("status", "provisioned")),
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
    status_value = normalize_machine_status(runtime.get("status"))
    return {
        **runtime,
        "mode": RUNTIME_MODE,
        "exists": True,
        "status": status_value,
        "ready": status_value in {"running", "ready", "stub"},
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


def start_user_runtime_bootstrap(user_id: str) -> dict[str, Any]:
    runtime = memory_store.get_user_runtime(user_id)
    if not runtime:
        raise DedalusRuntimeError("No runtime exists for this user.")
    if runtime.get("provider") != "dedalus":
        raise DedalusRuntimeError("Bootstrap is only available for Dedalus runtimes.")

    machine_id = runtime.get("machine_id")
    if not machine_id:
        raise DedalusRuntimeError("Runtime does not have a Dedalus machine_id.")
    if machine_id.startswith("stub-"):
        raise DedalusRuntimeError("Cannot bootstrap a stub runtime.")
    if not HIVE_REPO_URL:
        raise DedalusRuntimeError("Set HIVE_REPO_URL before bootstrapping a VM.")

    runtime = memory_store.upsert_user_runtime(
        user_id,
        {
            **runtime,
            "bootstrap_status": "running",
            "bootstrap_error": None,
            "bootstrap_steps": [],
        },
    )

    steps = run_bootstrap_steps(user_id=user_id, runtime=runtime, machine_id=machine_id)
    final_status = "succeeded" if all(step.get("ok") for step in steps) else "failed"

    runtime = memory_store.upsert_user_runtime(
        user_id,
        {
            **memory_store.get_user_runtime(user_id),
            "bootstrap_status": final_status,
            "bootstrap_steps": steps,
            "bootstrap_error": None
            if final_status == "succeeded"
            else first_failed_step_error(steps),
        },
    )

    if final_status == "succeeded":
        preview = create_runtime_preview(machine_id)
        runtime = memory_store.upsert_user_runtime(
            user_id,
            {
                **runtime,
                "runtime_preview": preview,
                "runtime_url": preview.get("url"),
            },
        )

    return {
        **runtime,
        "steps": steps,
        "message": f"Dedalus bootstrap {final_status}.",
    }


def run_bootstrap_steps(
    user_id: str,
    runtime: dict[str, Any],
    machine_id: str,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    commands = build_bootstrap_commands()

    for step_name, command, timeout_ms in commands:
        step_result = run_machine_command(
            machine_id=machine_id,
            step_name=step_name,
            command=command,
            timeout_ms=timeout_ms,
        )
        steps.append(step_result)
        memory_store.upsert_user_runtime(
            user_id,
            {
                **runtime,
                "bootstrap_status": "running"
                if step_result.get("ok")
                else "failed",
                "bootstrap_steps": steps,
                "bootstrap_execution_id": step_result.get("execution_id"),
                "bootstrap_execution": step_result.get("execution"),
                "bootstrap_output": step_result.get("output"),
            },
        )
        runtime = memory_store.get_user_runtime(user_id) or runtime
        if not step_result.get("ok"):
            break

    return steps


def build_bootstrap_commands() -> list[tuple[str, str, int]]:
    app_dir = shell_quote(HIVE_REMOTE_APP_DIR)
    repo_url = shell_quote(HIVE_REPO_URL)
    backend_subdir = shell_quote(HIVE_BACKEND_SUBDIR)
    home = shell_quote(DEDALUS_HOME)
    provider_model = shell_quote(
        os.getenv("OPENCLAW_PROVIDER_MODEL", "google/gemini-3-flash-preview")
    )
    gemini_key = shell_quote(os.getenv("GEMINI_API_KEY", ""))

    env_prefix = dedalus_env_prefix()

    return [
        (
            "fix-home-ownership",
            (
                "if command -v sudo >/dev/null 2>&1; then "
                f"sudo chown -R machine:machine {home}; "
                f"else chown -R machine:machine {home}; fi"
            ),
            120000,
        ),
        (
            "prepare-runtime-directories",
            (
                f"{env_prefix} && mkdir -p {home}/.tmp {home}/.local/bin "
                f"{home}/.cargo/bin {home}/.npm-global "
                f"{home}/.npm-cache {home}/.openclaw "
                f"{home}/.compile-cache {home}/.hive-logs {home}/.hive-run"
            ),
            120000,
        ),
        (
            "clone-or-update-repo",
            (
                f"{env_prefix} && rm -f {home}/.gitconfig ~/.gitconfig && "
                f"export GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null && "
                f"rm -rf {app_dir} && git clone {repo_url} {app_dir}"
            ),
            300000,
        ),
        (
            "install-python-requirements",
            (
                f"{env_prefix} && cd {app_dir}/{backend_subdir} && "
                f"cd {home} && curl -fsSL https://github.com/astral-sh/uv/releases/download/0.4.0/uv-x86_64-unknown-linux-musl.tar.gz | tar -xz && "
                f"mv uv-x86_64-unknown-linux-musl/uv {home}/.local/bin/uv && "
                "rm -rf uv-x86_64-unknown-linux-musl && "
                f"cd {app_dir}/{backend_subdir} && rm -rf .venv && "
                f"{home}/.local/bin/uv venv .venv --python /usr/bin/python3 && "
                f"export UV_LINK_MODE=copy && "
                f"VIRTUAL_ENV=$PWD/.venv {home}/.local/bin/uv pip install --refresh -r requirements.txt"
            ),
            900000,
        ),
        (
            "install-node-if-missing",
            (
                f"{env_prefix} && command -v node >/dev/null 2>&1 || "
                f"(cd {home} && "
                "curl -fsSL https://nodejs.org/dist/v20.12.2/node-v20.12.2-linux-x64.tar.xz | tar -xJ && "
                f"cp -rn node-v20.12.2-linux-x64/* {home}/.local/ && "
                "rm -rf node-v20.12.2-linux-x64)"
            ),
            300000,
        ),
        (
            "install-openclaw",
            (
                f"{env_prefix} && command -v openclaw || "
                "npm install -g openclaw@latest"
            ),
            600000,
        ),
        (
            "configure-openclaw",
            (
                f"{env_prefix} && "
                "openclaw config set gateway.mode local && "
                "openclaw config set gateway.bind loopback && "
                "openclaw config set gateway.port 18789 && "
                "openclaw config set gateway.http.endpoints.chatCompletions.enabled true && "
                f"openclaw config set agents.defaults.model.primary {provider_model} && "
                f"openclaw config set env.vars.GEMINI_API_KEY {gemini_key}"
            ),
            300000,
        ),
        (
            "write-hive-env",
            (
                f"{env_prefix} && cd {app_dir}/{backend_subdir} && "
                "printf '%s\\n' "
                "'HIVE_STATE_PATH=data/hive_state.json' "
                "'HIVE_RUNTIME_MODE=dedalus_worker' "
                "'HIVE_MEMPALACE_ENABLED=true' "
                "'HIVE_MEMPALACE_PATH=data/mempalace' "
                "'HIVE_MEMPALACE_AGENT=hive_brain' "
                "'HIVE_OPENCLAW_BOOTSTRAP_STATUS=installed' "
                "'OPENCLAW_URL=http://127.0.0.1:18789/v1/chat/completions' "
                "'OPENCLAW_HEALTH_URL=http://127.0.0.1:18789/' "
                "'OPENCLAW_CHAT_MODEL=openclaw' "
                f"'OPENCLAW_PROVIDER_MODEL={os.getenv('OPENCLAW_PROVIDER_MODEL', 'google/gemini-3-flash-preview')}' "
                f"'GEMINI_API_KEY={os.getenv('GEMINI_API_KEY', '')}' "
                f"'PATH={DEDALUS_HOME}/.npm-global/bin:$PATH' "
                "> .env"
            ),
            120000,
        ),
        (
            "start-openclaw",
            (
                f"{env_prefix} && pgrep -f openclaw-gateway >/dev/null || "
                f"(printf '%s\\n' '#!/bin/bash' "
                f"'export PATH={DEDALUS_HOME}/.npm-global/bin:$PATH' "
                f"'export HOME={DEDALUS_HOME}' "
                f"'export OPENCLAW_STATE_DIR={DEDALUS_HOME}/.openclaw' "
                f"'export NODE_COMPILE_CACHE={DEDALUS_HOME}/.compile-cache' "
                "'export OPENCLAW_NO_RESPAWN=1' "
                f"'exec openclaw gateway run --auth none > {DEDALUS_HOME}/.openclaw/gateway.log 2>&1' "
                f"> {DEDALUS_HOME}/start-openclaw.sh && "
                f"chmod +x {DEDALUS_HOME}/start-openclaw.sh && "
                f"setsid {DEDALUS_HOME}/start-openclaw.sh </dev/null >/dev/null 2>&1 & "
                "sleep 10)"
            ),
            180000,
        ),
        (
            "start-hive-backend",
            (
                f"{env_prefix} && cd {app_dir}/{backend_subdir} && "
                "if [ -f "
                f"{DEDALUS_HOME}/.hive-run/hive-backend.pid"
                " ]; then old_pid=$(cat "
                f"{DEDALUS_HOME}/.hive-run/hive-backend.pid"
                "); kill $old_pid >/dev/null 2>&1 || true; fi && "
                "setsid .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8010 "
                f"> {DEDALUS_HOME}/.hive-logs/hive-backend.log 2>&1 "
                f"< /dev/null & echo $! > {DEDALUS_HOME}/.hive-run/hive-backend.pid && "
                "sleep 5 && kill -0 $(cat "
                f"{DEDALUS_HOME}/.hive-run/hive-backend.pid"
                ")"
            ),
            180000,
        ),
        (
            "verify-hive-backend",
            (
                f"{env_prefix} && curl -sS -o /dev/null -w '%{{http_code}}' "
                "http://127.0.0.1:8010/health"
            ),
            120000,
        ),
    ]


def run_machine_command(
    machine_id: str,
    step_name: str,
    command: str,
    timeout_ms: int,
) -> dict[str, Any]:
    client = get_client()
    try:
        execution = client.machines.executions.create(
            machine_id=machine_id,
            command=["/bin/bash", "-c", command],
            timeout_ms=timeout_ms,
        )
    except Exception as exc:
        return {
            "name": step_name,
            "ok": False,
            "status": "failed",
            "execution_id": None,
            "execution": {},
            "output": {"stderr": str(exc)},
        }

    execution_data = model_to_dict(execution)
    execution_id = execution_data.get("execution_id")

    if execution_id:
        try:
            execution_data = wait_for_execution(
                machine_id=machine_id,
                execution_id=execution_id,
            )
        except Exception as exc:
            execution_data = {
                **execution_data,
                "status": "failed",
                "error_message": str(exc),
            }
        output_data = get_execution_output(
            machine_id=machine_id,
            execution_id=execution_id,
        )
    else:
        output_data = {"error": "Dedalus did not return an execution_id."}

    status = normalize_execution_status(execution_data.get("status"))
    return {
        "name": step_name,
        "ok": status == "succeeded",
        "status": status,
        "execution_id": execution_id,
        "execution": execution_data,
        "output": output_data,
    }


def wait_for_execution(machine_id: str, execution_id: str) -> dict[str, Any]:
    client = get_client()
    while True:
        execution = model_to_dict(
            client.machines.executions.retrieve(
                machine_id=machine_id,
                execution_id=execution_id,
            )
        )
        status = normalize_execution_status(execution.get("status"))
        if status in {"succeeded", "failed", "cancelled", "expired"}:
            return execution
        time.sleep(1)


def get_execution_output(machine_id: str, execution_id: str) -> dict[str, Any]:
    try:
        return model_to_dict(
            get_client().machines.executions.output(
                machine_id=machine_id,
                execution_id=execution_id,
            )
        )
    except Exception as exc:
        return {"error": str(exc)}


def dedalus_env_prefix() -> str:
    return (
        f"export HOME={shell_quote(DEDALUS_HOME)} && "
        f"export PATH={shell_quote(DEDALUS_HOME)}/.npm-global/bin:$PATH && "
        f"export PATH={shell_quote(DEDALUS_HOME)}/.local/bin:$PATH && "
        f"export PATH={shell_quote(DEDALUS_HOME)}/.cargo/bin:$PATH && "
        f"export NPM_CONFIG_PREFIX={shell_quote(DEDALUS_HOME)}/.npm-global && "
        f"export NPM_CONFIG_CACHE={shell_quote(DEDALUS_HOME)}/.npm-cache && "
        f"export TMPDIR={shell_quote(DEDALUS_HOME)}/.tmp && "
        f"export UV_CACHE_DIR={shell_quote(DEDALUS_HOME)}/.uv-cache && "
        "export UV_PYTHON_DOWNLOADS=never && "
        f"export OPENCLAW_STATE_DIR={shell_quote(DEDALUS_HOME)}/.openclaw && "
        f"export NODE_COMPILE_CACHE={shell_quote(DEDALUS_HOME)}/.compile-cache && "
        "export OPENCLAW_NO_RESPAWN=1"
    )


def shell_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def first_failed_step_error(steps: list[dict[str, Any]]) -> str:
    for step in steps:
        if step.get("ok"):
            continue
        output = step.get("output") or {}
        stderr = output.get("stderr") if isinstance(output, dict) else None
        return stderr or f"Bootstrap step failed: {step.get('name')}"
    return "Bootstrap execution failed."


def get_user_runtime_bootstrap_status(user_id: str) -> dict[str, Any]:
    runtime = memory_store.get_user_runtime(user_id)
    if not runtime:
        raise DedalusRuntimeError("No runtime exists for this user.")

    machine_id = runtime.get("machine_id")
    execution_id = runtime.get("bootstrap_execution_id")
    if not machine_id or not execution_id:
        return {
            **runtime,
            "bootstrap_status": runtime.get("bootstrap_status", "not_started"),
            "message": "No bootstrap execution has been started."
            if not runtime.get("bootstrap_steps")
            else "Bootstrap step history is available.",
        }

    if machine_id.startswith("stub-"):
        return {
            **runtime,
            "bootstrap_status": "stub",
            "message": "Stub runtimes cannot be bootstrapped.",
        }

    client = get_client()
    execution_data = model_to_dict(
        client.machines.executions.retrieve(
            machine_id=machine_id,
            execution_id=execution_id,
        )
    )
    output_data = None
    try:
        output_data = model_to_dict(
            client.machines.executions.output(
                machine_id=machine_id,
                execution_id=execution_id,
            )
        )
    except Exception as exc:
        output_data = {"error": str(exc)}

    bootstrap_status = normalize_execution_status(execution_data.get("status"))
    updates: dict[str, Any] = {
        **runtime,
        "bootstrap_status": bootstrap_status,
        "bootstrap_execution": execution_data,
        "bootstrap_output": output_data,
    }

    if bootstrap_status == "succeeded" and not runtime.get("runtime_url"):
        preview = create_runtime_preview(machine_id)
        updates["runtime_preview"] = preview
        updates["runtime_url"] = preview.get("url")
    elif bootstrap_status in {"failed", "cancelled", "expired"}:
        updates["bootstrap_error"] = (
            execution_data.get("error_message") or "Bootstrap execution failed."
        )

    runtime = memory_store.upsert_user_runtime(user_id, updates)
    return {
        **runtime,
        "execution": execution_data,
        "output": output_data,
    }


def bootstrap_env() -> dict[str, str]:
    env = {
        "HIVE_REPO_URL": HIVE_REPO_URL,
        "HIVE_REMOTE_APP_DIR": HIVE_REMOTE_APP_DIR,
        "HIVE_BACKEND_SUBDIR": HIVE_BACKEND_SUBDIR,
        "OPENCLAW_PROVIDER_MODEL": os.getenv(
            "OPENCLAW_PROVIDER_MODEL", "google/gemini-3-flash-preview"
        ),
    }
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key:
        env["GEMINI_API_KEY"] = gemini_key
    return env


def create_runtime_preview(machine_id: str) -> dict[str, Any]:
    try:
        preview = get_client().machines.previews.create(
            machine_id=machine_id,
            port=8010,
            protocol="http",
            visibility=DEDALUS_BOOTSTRAP_PREVIEW_VISIBILITY,
        )
        return model_to_dict(preview)
    except Exception as exc:
        return {"error": str(exc)}


def create_dedalus_machine() -> dict[str, Any]:
    if not DEDALUS_API_KEY:
        return {
            "machine_id": f"stub-{memory_store.now_iso()}",
            "status": "stub",
            "stub": True,
            "error": "DEDALUS_API_KEY is not set; recorded a stub runtime.",
        }

    client = get_client()
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
        client = get_client()
    except ImportError as exc:
        return {"ok": False, "error": f"dedalus-sdk is not installed: {exc}"}
    except DedalusRuntimeError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        machine = client.machines.retrieve(machine_id=machine_id)
        data = model_to_dict(machine)
        return {
            "ok": True,
            "status": normalize_machine_status(data.get("status")),
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
        client = get_client()
    except ImportError as exc:
        return {"ok": False, "error": f"dedalus-sdk is not installed: {exc}"}
    except DedalusRuntimeError as exc:
        return {"ok": False, "error": str(exc)}

    try:
        machine = model_to_dict(client.machines.retrieve(machine_id=machine_id))
        revision = (
            machine.get("status", {}).get("revision")
            if isinstance(machine.get("status"), dict)
            else None
        )
        result = client.machines.delete(machine_id=machine_id, if_match=revision)
        return {"ok": True, "result": model_to_dict(result)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def get_client() -> Any:
    if not DEDALUS_API_KEY:
        raise DedalusRuntimeError("DEDALUS_API_KEY is not set.")
    try:
        from dedalus_sdk import Dedalus
    except ImportError as exc:
        raise DedalusRuntimeError(
            "Install dedalus-sdk in the backend venv before real machine provisioning."
        ) from exc
    return Dedalus(api_key=DEDALUS_API_KEY, dedalus_org_id=DEDALUS_ORG_ID)


def model_to_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "to_dict"):
        return json_safe(value.to_dict())
    if hasattr(value, "model_dump"):
        return json_safe(value.model_dump())
    if isinstance(value, dict):
        return json_safe(value)
    return {"value": str(value)}


def normalize_machine_status(status: Any) -> str:
    if isinstance(status, str):
        return status
    if isinstance(status, dict):
        for key in ("state", "status", "phase", "name"):
            value = status.get(key)
            if isinstance(value, str):
                return value
        if status.get("running") is True:
            return "running"
        return "provisioning"
    if status is None:
        return "unknown"
    return str(status)


def normalize_execution_status(status: Any) -> str:
    if isinstance(status, str):
        return status
    if status is None:
        return "unknown"
    return str(status)


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)
