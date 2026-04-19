from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Any


BACKEND_DIR = Path(__file__).resolve().parent
LOG_DIR = BACKEND_DIR / "data" / "telegram_worker_logs"
PID_DIR = BACKEND_DIR / "data" / "telegram_worker_pids"
_workers: dict[str, subprocess.Popen[bytes]] = {}


def worker_command(agent_id: str) -> str:
    return f"HIVE_AGENT_ID={agent_id} {sys.executable} telegram_bot.py"


def get_worker_status(agent_id: str) -> dict[str, Any]:
    process = _workers.get(agent_id)
    exit_code = process.poll() if process else None
    running = bool(process and exit_code is None)
    pid = process.pid if process else read_pid(agent_id)

    if process and exit_code is not None:
        _workers.pop(agent_id, None)
        remove_pid(agent_id)
        pid = None
    elif process:
        write_pid(agent_id, process.pid)
    elif pid and is_pid_running(pid):
        running = True
    elif pid:
        remove_pid(agent_id)
        pid = None

    return {
        "agent_id": agent_id,
        "running": running,
        "pid": pid,
        "exit_code": exit_code,
        "command": worker_command(agent_id),
        "log_path": str(log_path(agent_id)),
    }


def start_worker(agent_id: str) -> dict[str, Any]:
    status = get_worker_status(agent_id)
    if status["running"]:
        return {**status, "started": False, "message": "Telegram worker already running."}

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["HIVE_AGENT_ID"] = agent_id
    env["PYTHONUNBUFFERED"] = "1"

    with log_path(agent_id).open("ab") as log_file:
        process = subprocess.Popen(
            [sys.executable, "telegram_bot.py"],
            cwd=BACKEND_DIR,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    _workers[agent_id] = process
    write_pid(agent_id, process.pid)
    return {
        **get_worker_status(agent_id),
        "started": True,
        "message": "Telegram worker started.",
    }


def stop_worker(agent_id: str) -> dict[str, Any]:
    process = _workers.get(agent_id)
    pid = process.pid if process else read_pid(agent_id)
    if not pid or not is_pid_running(pid):
        _workers.pop(agent_id, None)
        remove_pid(agent_id)
        return {
            **get_worker_status(agent_id),
            "stopped": False,
            "message": "Telegram worker is not running.",
        }

    os.killpg(pid, signal.SIGTERM)
    if process:
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(pid, signal.SIGKILL)
            process.wait(timeout=5)

    _workers.pop(agent_id, None)
    remove_pid(agent_id)
    return {
        **get_worker_status(agent_id),
        "stopped": True,
        "message": "Telegram worker stopped.",
    }


def log_path(agent_id: str) -> Path:
    return LOG_DIR / f"{safe_agent_id(agent_id)}.log"


def pid_path(agent_id: str) -> Path:
    return PID_DIR / f"{safe_agent_id(agent_id)}.pid"


def safe_agent_id(agent_id: str) -> str:
    return "".join(
        character for character in agent_id if character.isalnum() or character in "-_"
    )


def write_pid(agent_id: str, pid: int) -> None:
    PID_DIR.mkdir(parents=True, exist_ok=True)
    pid_path(agent_id).write_text(str(pid), encoding="utf-8")


def read_pid(agent_id: str) -> int | None:
    path = pid_path(agent_id)
    if not path.exists():
        return None

    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        remove_pid(agent_id)
        return None


def remove_pid(agent_id: str) -> None:
    pid_path(agent_id).unlink(missing_ok=True)


def is_pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False
