import time
from pathlib import Path

from core.performance_mode import configured_performance_mode, performance_settings
from memory.json_store import read_json_file, update_json_file, write_json_atomic
from memory.supabase_sync import sync_memory_state_safely

STATE_PATH = Path(__file__).with_name("ui_state.json")

DEFAULT_UI_STATE = {
    "assistant_name": "Axel",
    "visible": False,
    "status": "INATIVO",
    "mode": "comando",
    "last_heard": "",
    "last_response": "",
    "last_command": "",
    "microphone": "",
    "assistant_style": "jarvis",
    "performance_mode": configured_performance_mode(),
    "performance_settings": performance_settings().as_dict(),
    "voice_profile": "",
    "hotword_enabled": False,
    "conversation_mode": False,
    "dictation_mode": False,
    "axel_brain_plan": {},
    "axel_brain_brief": {},
    "last_route_trace": {},
    "skill_suggestions": [],
    "observability": {},
    "active_panel": "",
    "open_panels": [],
    "map_panel_open": False,
    "map_request": {},
    "notifications": [],
    "voice_notifications_enabled": False,
    "voice_notifications_pending": [],
    "history": [],
    "updated_at": 0.0,
}


def load_ui_state() -> dict:
    data = read_json_file(STATE_PATH, {}, validator=lambda value: isinstance(value, dict))
    merged = dict(DEFAULT_UI_STATE)
    if isinstance(data, dict):
        merged.update(data)
        return _normalize_ui_state(merged)
    return _normalize_ui_state(dict(DEFAULT_UI_STATE))


def _normalize_ui_state(state: dict) -> dict:
    payload = dict(DEFAULT_UI_STATE)
    if isinstance(state, dict):
        payload.update(state)
    settings = performance_settings(str(payload.get("performance_mode") or configured_performance_mode()))
    payload["performance_mode"] = settings.mode
    payload["performance_settings"] = settings.as_dict()
    return payload


def save_ui_state(state: dict):
    payload = _normalize_ui_state(state)
    payload["updated_at"] = time.time()

    write_json_atomic(STATE_PATH, payload, indent=2)
    sync_memory_state_safely("ui_state", payload, category="ui")


def update_ui_state(patch: dict):
    def apply_patch(state: dict) -> dict:
        state = _normalize_ui_state(state)
        state.update(patch or {})
        state["updated_at"] = time.time()
        return state

    payload = update_json_file(
        STATE_PATH,
        dict(DEFAULT_UI_STATE),
        apply_patch,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    sync_memory_state_safely("ui_state", payload, category="ui")


def append_ui_history(role: str, text: str, max_items: int = 8):
    content = str(text or "").strip()
    if not content:
        return

    def apply_history(state: dict) -> dict:
        state = _normalize_ui_state(state)
        history = list(state.get("history") or [])
        history.append({"role": str(role or "system"), "text": content, "at": time.time()})
        state["history"] = history[-max(1, int(max_items)) :]
        state["updated_at"] = time.time()
        return state

    payload = update_json_file(
        STATE_PATH,
        dict(DEFAULT_UI_STATE),
        apply_history,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    sync_memory_state_safely("ui_state", payload, category="ui")


def append_ui_notification(kind: str, text: str, *, level: str = "info", max_items: int = 10):
    content = str(text or "").strip()
    if not content:
        return

    def apply_notification(state: dict) -> dict:
        state = _normalize_ui_state(state)
        notifications = list(state.get("notifications") or [])
        notifications.append(
            {
                "kind": str(kind or "general"),
                "level": str(level or "info"),
                "text": content,
                "at": time.time(),
            }
        )
        state["notifications"] = notifications[-max(1, int(max_items)) :]
        state["updated_at"] = time.time()
        return state

    payload = update_json_file(
        STATE_PATH,
        dict(DEFAULT_UI_STATE),
        apply_notification,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    sync_memory_state_safely("ui_state", payload, category="ui")


def append_voice_notification(text: str, *, source: str = "background", max_items: int = 5):
    content = str(text or "").strip()
    if not content:
        return

    def apply_voice_notification(state: dict) -> dict:
        state = _normalize_ui_state(state)
        pending = list(state.get("voice_notifications_pending") or [])
        pending.append(
            {
                "source": str(source or "background"),
                "text": content,
                "at": time.time(),
            }
        )
        state["voice_notifications_pending"] = pending[-max(1, int(max_items)) :]
        state["updated_at"] = time.time()
        return state

    payload = update_json_file(
        STATE_PATH,
        dict(DEFAULT_UI_STATE),
        apply_voice_notification,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    sync_memory_state_safely("ui_state", payload, category="ui")


def pop_next_voice_notification() -> dict:
    popped: dict = {}

    def apply_pop(state: dict) -> dict:
        nonlocal popped
        state = _normalize_ui_state(state)
        pending = [item for item in (state.get("voice_notifications_pending") or []) if isinstance(item, dict)]
        if pending:
            popped = dict(pending[0])
            state["voice_notifications_pending"] = pending[1:]
            state["updated_at"] = time.time()
        return state

    payload = update_json_file(
        STATE_PATH,
        dict(DEFAULT_UI_STATE),
        apply_pop,
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    sync_memory_state_safely("ui_state", payload, category="ui")
    return popped


def reset_ui_state():
    save_ui_state(dict(DEFAULT_UI_STATE))
