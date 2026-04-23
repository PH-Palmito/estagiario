import json
import os
import time
from pathlib import Path

from memory.implementation_handoff import load_implementation_handoff


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
HANDOFF_APPLICATIONS_PATH = MEMORY_DIR / "handoff_applications.json"


def _save_json(path: Path, payload: dict):
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _handoff_key(handoff: dict) -> str:
    title = str(handoff.get("title", "")).strip().lower()
    files = ",".join(str(item) for item in handoff.get("files", []))
    return f"{title}|{files}"


def _default_state() -> dict:
    handoff = load_implementation_handoff()
    status = "ready" if handoff.get("status") == "ready" else "blocked"
    return {
        "generated_at": time.time(),
        "status": status,
        "handoff_key": _handoff_key(handoff) if handoff.get("title") else "",
        "handoff": handoff,
        "last_note": "",
        "started_at": 0.0,
        "applied_at": 0.0,
        "failed_at": 0.0,
    }


def sync_handoff_application() -> dict:
    state = _load_json(HANDOFF_APPLICATIONS_PATH)
    if not isinstance(state, dict) or "status" not in state:
        state = _default_state()

    handoff = load_implementation_handoff()
    handoff_key = _handoff_key(handoff) if handoff.get("title") else ""
    old_key = str(state.get("handoff_key", "")).strip()

    if handoff_key != old_key:
        state = _default_state()
    else:
        state["handoff"] = handoff
        if handoff.get("status") != "ready":
            state["status"] = "blocked"

    state["generated_at"] = time.time()
    _save_json(HANDOFF_APPLICATIONS_PATH, state)
    return state


def load_handoff_application() -> dict:
    return sync_handoff_application()


def mark_handoff_started(note: str = "") -> dict:
    state = sync_handoff_application()
    if state.get("handoff", {}).get("status") != "ready":
        return state
    state["status"] = "in_progress"
    state["last_note"] = str(note or "").strip()
    state["started_at"] = time.time()
    _save_json(HANDOFF_APPLICATIONS_PATH, state)
    return state


def mark_handoff_applied(note: str = "") -> dict:
    state = sync_handoff_application()
    if state.get("handoff", {}).get("status") != "ready":
        return state
    state["status"] = "applied"
    state["last_note"] = str(note or "").strip()
    state["applied_at"] = time.time()
    _save_json(HANDOFF_APPLICATIONS_PATH, state)
    return state


def mark_handoff_failed(note: str = "") -> dict:
    state = sync_handoff_application()
    if state.get("handoff", {}).get("status") != "ready":
        return state
    state["status"] = "failed"
    state["last_note"] = str(note or "").strip()
    state["failed_at"] = time.time()
    _save_json(HANDOFF_APPLICATIONS_PATH, state)
    return state
