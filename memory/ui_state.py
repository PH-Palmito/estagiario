import json
import os
import time
from pathlib import Path


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
    "voice_profile": "",
    "hotword_enabled": False,
    "conversation_mode": False,
    "dictation_mode": False,
    "history": [],
    "updated_at": 0.0,
}


def load_ui_state() -> dict:
    if not STATE_PATH.exists():
        return dict(DEFAULT_UI_STATE)

    try:
        data = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        merged = dict(DEFAULT_UI_STATE)
        if isinstance(data, dict):
            merged.update(data)
        return merged
    except Exception:
        return dict(DEFAULT_UI_STATE)


def save_ui_state(state: dict):
    payload = dict(DEFAULT_UI_STATE)
    if isinstance(state, dict):
        payload.update(state)
    payload["updated_at"] = time.time()

    tmp_path = STATE_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, STATE_PATH)


def update_ui_state(patch: dict):
    state = load_ui_state()
    state.update(patch or {})
    save_ui_state(state)


def append_ui_history(role: str, text: str, max_items: int = 8):
    content = str(text or "").strip()
    if not content:
        return

    state = load_ui_state()
    history = list(state.get("history") or [])
    history.append({"role": str(role or "system"), "text": content, "at": time.time()})
    state["history"] = history[-max(1, int(max_items)) :]
    save_ui_state(state)


def reset_ui_state():
    save_ui_state(dict(DEFAULT_UI_STATE))
