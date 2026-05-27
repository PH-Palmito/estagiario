from __future__ import annotations

from typing import Any


def format_background_notification(task: dict[str, Any]) -> dict[str, str]:
    name = str(task.get("name") or "tarefa").strip() or "tarefa"
    status = str(task.get("status") or "").strip()
    if status == "failed":
        detail = str(task.get("error") or task.get("message") or "sem detalhe").strip()
        return {
            "kind": "background",
            "level": "warning",
            "text": f"{name} falhou: {detail[:220]}",
        }

    message = str(task.get("message") or "concluida").strip()
    return {
        "kind": "background",
        "level": "info",
        "text": f"{name} terminou: {message[:220]}",
    }


def publish_background_notification(task: dict[str, Any]) -> bool:
    payload = format_background_notification(task)
    if not payload.get("text"):
        return False
    try:
        from memory.ui_state import append_ui_notification, append_voice_notification, load_ui_state
        from services.voice_notification_service import plan_background_voice_notification

        append_ui_notification(
            payload["kind"],
            payload["text"],
            level=payload["level"],
        )
        voice_plan = plan_background_voice_notification(task, load_ui_state())
        if voice_plan.should_speak:
            append_voice_notification(voice_plan.text, source="background")
        return True
    except Exception:
        return False
