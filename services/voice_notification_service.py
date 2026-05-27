from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable
from typing import Any


IMPORTANT_BACKGROUND_TASKS = {
    "daily_briefing",
    "investment_financial_report",
    "investment_refresh_public_wallet",
    "image_analyze_screen",
    "image_analyze_screen_graph",
}

SILENT_UI_MODES = {"silencioso", "silent", "foco", "focus", "modo_foco", "focus_mode"}


@dataclass(frozen=True)
class VoiceNotificationPlan:
    should_speak: bool
    text: str
    reason: str


def _compact_voice_text(text: str, limit: int = 180) -> str:
    compact = " ".join(str(text or "").split()).strip()
    if len(compact) <= limit:
        return compact
    return compact[:limit].rsplit(" ", 1)[0].rstrip(" ,.;") + "."


def plan_background_voice_notification(
    notification: dict[str, Any],
    ui_state: dict[str, Any] | None = None,
) -> VoiceNotificationPlan:
    state = ui_state if isinstance(ui_state, dict) else {}
    if not bool(state.get("voice_notifications_enabled")):
        return VoiceNotificationPlan(False, "", "notificacoes por voz desligadas")

    ui_mode = str(state.get("mode") or "").strip().lower()
    active_panel = str(state.get("active_panel") or "").strip().lower()
    if ui_mode in SILENT_UI_MODES or active_panel in SILENT_UI_MODES:
        return VoiceNotificationPlan(False, "", "modo silencioso ou foco ativo")

    name = str(notification.get("name") or "tarefa").strip() or "tarefa"
    status = str(notification.get("status") or "").strip()
    is_failure = status == "failed"
    is_important = name in IMPORTANT_BACKGROUND_TASKS
    if not is_failure and not is_important:
        return VoiceNotificationPlan(False, "", "tarefa sem prioridade para fala")

    if is_failure:
        detail = _compact_voice_text(str(notification.get("error") or notification.get("message") or "sem detalhe"))
        return VoiceNotificationPlan(True, f"{name} falhou. {detail}", "falha importante")

    message = _compact_voice_text(str(notification.get("message") or "concluida"))
    return VoiceNotificationPlan(True, f"{name} terminou. {message}", "tarefa importante concluida")


def ui_state_blocks_voice_notification(ui_state: dict[str, Any] | None) -> bool:
    state = ui_state if isinstance(ui_state, dict) else {}
    ui_mode = str(state.get("mode") or "").strip().lower()
    active_panel = str(state.get("active_panel") or "").strip().lower()
    return ui_mode in SILENT_UI_MODES or active_panel in SILENT_UI_MODES


def speak_next_pending_voice_notification(
    *,
    voice_mode: bool,
    speak: Callable[..., object],
    load_ui_state: Callable[[], dict],
    pop_next_voice_notification: Callable[[], dict],
) -> bool:
    if not voice_mode:
        return False
    state = load_ui_state()
    if ui_state_blocks_voice_notification(state):
        return False
    pending = state.get("voice_notifications_pending") or []
    if not pending:
        return False
    item = pop_next_voice_notification()
    text = str(item.get("text") or "").strip()
    if not text:
        return False
    speak(text, interrupt_current=False, wait_for_playback=False)
    return True
