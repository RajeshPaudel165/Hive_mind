from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from typing import Any

from dotenv import load_dotenv

import main
import memory_store
import telegram_bot


load_dotenv()

PULSE_INTERVAL_SECONDS = int(os.getenv("HIVE_PULSE_INTERVAL_SECONDS", "3600"))
PULSE_LOOP_SLEEP_SECONDS = int(os.getenv("HIVE_PULSE_LOOP_SLEEP_SECONDS", "30"))


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def seconds_since(value: str | None) -> float | None:
    timestamp = parse_iso(value)
    if timestamp is None:
        return None
    return (datetime.now(UTC) - timestamp).total_seconds()


def session_is_due(session: dict[str, Any], force: bool = False) -> bool:
    if force:
        return True

    elapsed = seconds_since(session.get("last_pulse_sent_at"))
    return elapsed is None or elapsed >= PULSE_INTERVAL_SECONDS


def iter_pulse_candidates() -> list[tuple[str, dict[str, Any]]]:
    return memory_store.list_pulse_candidates()


def send_due_pulses(force: bool = False) -> list[dict[str, Any]]:
    results = []
    for pairing_code, session in iter_pulse_candidates():
        if not session_is_due(session, force=force):
            results.append(
                {
                    "pairing_code": pairing_code,
                    "sent": False,
                    "reason": "not_due",
                }
            )
            continue

        try:
            pulse = main.create_pulse_preview(pairing_code)
            telegram_bot.send_message(session["telegram_chat_id"], pulse["message"])
            memory_store.mark_pulse_sent(pairing_code, pulse["delivery"])
            results.append(
                {
                    "pairing_code": pairing_code,
                    "sent": True,
                    "delivery": pulse["delivery"],
                }
            )
        except Exception as exc:
            results.append(
                {
                    "pairing_code": pairing_code,
                    "sent": False,
                    "reason": str(exc),
                }
            )
    return results


def run_pulse_loop() -> None:
    print(
        "Pulse worker started. "
        f"interval={PULSE_INTERVAL_SECONDS}s sleep={PULSE_LOOP_SLEEP_SECONDS}s"
    )
    while True:
        try:
            results = send_due_pulses()
            for result in results:
                print(result)
        except KeyboardInterrupt:
            print("Pulse worker stopped.")
            return
        except Exception as exc:
            print(f"Pulse worker error: {exc}")

        time.sleep(PULSE_LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    run_pulse_loop()
