from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from threading import Thread


def send_startup_briefing_once(
    *,
    voice_mode: bool,
    args: Sequence[str],
    voice_preferences: dict,
    state_path: Path,
    greeting_variants: dict,
    next_phrase: Callable[[str, list[str], str], str],
    daily_briefing: Callable[[], str],
    output_response: Callable[..., None],
    now: datetime | None = None,
) -> bool:
    if "--no-startup-briefing" in args:
        return False
    if not bool(voice_preferences.get("startup_briefing_enabled", True)):
        return False

    now = now or datetime.now()
    today_key = now.date().isoformat()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state = state if isinstance(state, dict) else {}
    except Exception:
        state = {}

    if state.get("last_briefing_date") == today_key:
        already_delivered = next_phrase(
            "startup_briefing_already_delivered",
            greeting_variants["briefing_already_delivered"],
            "Briefing de hoje ja foi entregue. Estou em escuta e monitorando seus lembretes.",
        )
        output_response(
            already_delivered,
            voice_mode,
            interrupt_current_tts=True,
            wait_for_tts=True,
        )
        return True

    try:
        briefing = daily_briefing()
    except Exception:
        return False

    briefing = str(briefing or "").strip()
    if not briefing:
        return False

    output_response(
        briefing,
        voice_mode,
        interrupt_current_tts=True,
        wait_for_tts=True,
    )
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(
                {
                    "last_briefing_date": today_key,
                    "last_briefing_at": now.isoformat(timespec="seconds"),
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except Exception:
        pass
    return True


def schedule_startup_briefing_worker(
    *,
    args: Sequence[str],
    voice_mode: bool,
    send_startup_briefing: Callable[[bool], bool],
    delay_seconds: float = 2.0,
) -> bool:
    if "--no-startup-briefing" in args:
        return False

    try:
        def worker():
            time.sleep(delay_seconds)
            send_startup_briefing(voice_mode)

        Thread(
            target=worker,
            name="axel-startup-briefing",
            daemon=True,
        ).start()
        return True
    except Exception:
        send_startup_briefing(voice_mode)
        return False
