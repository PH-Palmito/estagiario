from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime


@dataclass
class ReminderAnnouncer:
    consume_due_training_reminder: Callable[[], dict]
    consume_due_reminders: Callable[[], list[dict]]
    output_response: Callable[..., None]
    now_fn: Callable[[], float] = time.time
    min_interval_seconds: float = 20.0
    night_sleep_prompt_hour: int = 23
    last_check_at: float = 0.0
    last_night_sleep_prompt_key: str = ""

    def maybe_announce_due_reminders(self, voice_mode: bool) -> bool:
        now = self.now_fn()
        if now - self.last_check_at < self.min_interval_seconds:
            return False
        self.last_check_at = now

        try:
            training_due = self.consume_due_training_reminder()
        except Exception:
            training_due = {}
        if training_due:
            text = str(training_due.get("text", "")).strip()
            if text:
                self._announce(text, voice_mode)
                return True

        try:
            due = self.consume_due_reminders()
        except Exception:
            return False

        message = reminder_message(due)
        if not message:
            return self.maybe_announce_night_sleep_prompt(voice_mode)

        self._announce(message, voice_mode)
        return True

    def maybe_announce_night_sleep_prompt(self, voice_mode: bool) -> bool:
        current = datetime.fromtimestamp(self.now_fn())
        if 5 <= current.hour < self.night_sleep_prompt_hour:
            return False

        prompt_key = current.strftime("%Y-%m-%d")
        if current.hour < 5:
            prompt_key = f"{prompt_key}-madrugada"
        if self.last_night_sleep_prompt_key == prompt_key:
            return False

        self.last_night_sleep_prompt_key = prompt_key
        self._announce(
            "Ja esta tarde. Se voce ainda estiver usando o PC sem urgencia, vale salvar o progresso e dormir.",
            voice_mode,
        )
        return True

    def _announce(self, message: str, voice_mode: bool) -> None:
        self.output_response(
            message,
            voice_mode,
            interrupt_current_tts=True,
            wait_for_tts=True,
        )


def reminder_message(due: list[dict] | None) -> str:
    due = due or []
    if not due:
        return ""

    if len(due) == 1:
        text = str(due[0].get("text", "")).strip()
        follow_up = str(due[0].get("follow_up_prompt", "")).strip()
        if due[0].get("source") == "agenda":
            if not text:
                return "Voce tem um compromisso vencido."
            return f"Agenda: {text}.{(' ' + follow_up) if follow_up else ''}"
        return f"Lembrete: {text}." if text else "Voce tem um lembrete vencido."

    texts = [str(item.get("text", "")).strip() for item in due if str(item.get("text", "")).strip()]
    if any(item.get("source") == "agenda" for item in due):
        return "Agenda e lembretes: " + "; ".join(texts[:3]) + "."
    return "Lembretes: " + "; ".join(texts[:3]) + "."
