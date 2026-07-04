from __future__ import annotations

import json
import time
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path
from threading import Thread

INTERACTIVE_STARTUP_BRIEFING_DELAY_SECONDS = 2.0
WINDOWS_STARTUP_BRIEFING_DELAY_SECONDS = 8.0


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
    force = "--force-startup-briefing" in args

    now = now or datetime.now()
    today_key = now.date().isoformat()
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        state = state if isinstance(state, dict) else {}
    except Exception:
        state = {}

    if state.get("last_briefing_date") == today_key and not force:
        return True

    try:
        briefing = daily_briefing()
    except Exception as exc:
        output_response(
            f"Nao consegui gerar o briefing automatico agora: {exc}",
            voice_mode,
            interrupt_current_tts=True,
            wait_for_tts=True,
        )
        return False

    briefing = str(briefing or "").strip()
    if not briefing:
        output_response(
            "O briefing automatico veio vazio agora. Posso tentar de novo quando voce pedir.",
            voice_mode,
            interrupt_current_tts=True,
            wait_for_tts=True,
        )
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
    delay_seconds: float | None = None,
) -> bool:
    if "--no-startup-briefing" in args:
        return False
    if delay_seconds is None:
        if "--force-startup-briefing" in args:
            delay_seconds = INTERACTIVE_STARTUP_BRIEFING_DELAY_SECONDS
        elif "--startup" in args:
            delay_seconds = WINDOWS_STARTUP_BRIEFING_DELAY_SECONDS
        else:
            delay_seconds = INTERACTIVE_STARTUP_BRIEFING_DELAY_SECONDS

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
