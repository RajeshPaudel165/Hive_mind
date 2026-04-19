from __future__ import annotations

import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from openclaw_client import get_openclaw_status


BACKEND_DIR = Path(__file__).resolve().parent
SCRIPT_PATH = BACKEND_DIR / "scripts" / "openclaw_local_start.sh"
LOG_DIR = BACKEND_DIR / "data" / "openclaw_logs"
PID_PATH = BACKEND_DIR / "data" / "openclaw_gateway.pid"
OPENCLAW_BOOTSTRAP_STATUS = os.getenv("HIVE_OPENCLAW_BOOTSTRAP_STATUS", "installed")
_process: subprocess.Popen[bytes] | None = None


def get_status() -> dict[str, Any]:
    status = get_openclaw_status()
    process = current_process()
    pid = process.pid if process else read_pid()

    if process and process.poll() is not None:
        clear_process()
        remove_pid()
        pid = None
    elif process:
        write_pid(process.pid)
    elif pid and not is_pid_running(pid):
        remove_pid()
        pid = None

    return {
        **status,
        "managed_pid": pid,
        "managed_running": bool(pid and is_pid_running(pid)),
        "log_path": str(log_path()),
        "start_script": str(SCRIPT_PATH),
    }


def ensure_running(timeout_seconds: float = 20) -> dict[str, Any]:
    status = get_status()
    if status.get("reachable"):
        return {**status, "started": False, "message": "OpenClaw already reachable."}
    if OPENCLAW_BOOTSTRAP_STATUS == "deferred":
        return {
            **status,
            "started": False,
            "deferred": True,
            "message": "OpenClaw install was deferred because node/npm were unavailable.",
        }

    start_status = start_gateway(wait=False)
    ready_status = wait_until_reachable(timeout_seconds=timeout_seconds)
    return {
        **ready_status,
        "started": start_status.get("started", False),
        "message": (
            "OpenClaw gateway started."
            if ready_status.get("reachable")
            else "OpenClaw gateway start requested, but health check is not ready yet."
        ),
    }


def start_gateway(wait: bool = True, timeout_seconds: float = 20) -> dict[str, Any]:
    status = get_status()
    if status.get("reachable"):
        return {**status, "started": False, "message": "OpenClaw already reachable."}
    if status.get("managed_running"):
        return {**status, "started": False, "message": "OpenClaw process already running."}

    if not SCRIPT_PATH.exists():
        return {
            **status,
            "started": False,
            "error": f"Missing OpenClaw start script: {SCRIPT_PATH}",
        }

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"

    with log_path().open("ab") as log_file:
        process = subprocess.Popen(
            [str(SCRIPT_PATH)],
            cwd=BACKEND_DIR,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    set_process(process)
    write_pid(process.pid)

    if wait:
        return {
            **wait_until_reachable(timeout_seconds=timeout_seconds),
            "started": True,
        }

    return {
        **get_status(),
        "started": True,
        "message": "OpenClaw gateway process started.",
    }


def stop_gateway() -> dict[str, Any]:
    process = current_process()
    pid = process.pid if process else read_pid()
    if not pid or not is_pid_running(pid):
        clear_process()
        remove_pid()
        return {
            **get_status(),
            "stopped": False,
            "message": "No managed OpenClaw process is running.",
        }

    os.killpg(pid, signal.SIGTERM)
    if process:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(pid, signal.SIGKILL)
            process.wait(timeout=5)

    clear_process()
    remove_pid()
    return {
        **get_status(),
        "stopped": True,
        "message": "Managed OpenClaw gateway stopped.",
    }


def wait_until_reachable(timeout_seconds: float) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    status = get_status()
    while time.monotonic() < deadline:
        status = get_status()
        if status.get("reachable"):
            return status
        time.sleep(1)
    return status


def current_process() -> subprocess.Popen[bytes] | None:
    return _process


def set_process(process: subprocess.Popen[bytes]) -> None:
    global _process
    _process = process


def clear_process() -> None:
    global _process
    _process = None


def log_path() -> Path:
    return LOG_DIR / "gateway.log"


def write_pid(pid: int) -> None:
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    PID_PATH.write_text(str(pid), encoding="utf-8")


def read_pid() -> int | None:
    if not PID_PATH.exists():
        return None
    try:
        return int(PID_PATH.read_text(encoding="utf-8").strip())
    except ValueError:
        remove_pid()
        return None


def remove_pid() -> None:
    PID_PATH.unlink(missing_ok=True)


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
