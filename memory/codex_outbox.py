import json
import os
import time
from pathlib import Path

from memory.codex_channel import load_codex_channel
from memory.codex_implementation_request import save_codex_implementation_request


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
CODEX_OUTBOX_PATH = MEMORY_DIR / "codex_outbox.json"


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


def _default_state() -> dict:
    return {
        "generated_at": time.time(),
        "pending": [],
        "sent": [],
        "last_enqueued_key": "",
        "last_sent_key": "",
    }


def load_codex_outbox() -> dict:
    data = _load_json(CODEX_OUTBOX_PATH)
    if isinstance(data, dict):
        base = _default_state()
        base.update(data)
        if not isinstance(base.get("pending"), list):
            base["pending"] = []
        if not isinstance(base.get("sent"), list):
            base["sent"] = []
        return base
    return _default_state()


def _message_entry_from_channel(channel: dict) -> dict:
    return {
        "message_key": str(channel.get("message_key", "")).strip(),
        "title": str(channel.get("title", "")).strip(),
        "trigger": str(channel.get("trigger", "")).strip(),
        "urgency": str(channel.get("urgency", "")).strip(),
        "status": "pending",
        "message": str(channel.get("message", "")).strip(),
        "next_action": str(channel.get("next_action", "")).strip(),
        "created_at": time.time(),
    }


def _message_entry_from_implementation_request(request: dict) -> dict:
    title = str(request.get("title", "")).strip()
    files = ",".join(str(file) for file in request.get("files", []))
    return {
        "message_key": f"implementation:{title.lower()}|{files}",
        "title": title or "Pedido de implementacao ao Codex",
        "trigger": "handoff-ready",
        "urgency": "normal",
        "status": "pending",
        "message": str(request.get("prompt", "")).strip(),
        "next_action": "Codex deve aplicar o handoff, validar e responder com resultado.",
        "kind": "implementation_request",
        "created_at": time.time(),
    }


def sync_codex_outbox(auto_enqueue: bool = True) -> dict:
    state = load_codex_outbox()
    channel = load_codex_channel()
    message_key = str(channel.get("message_key", "")).strip()

    if auto_enqueue and bool(channel.get("should_notify")) and message_key:
        known_keys = {
            str(item.get("message_key", "")).strip()
            for item in list(state.get("pending", [])) + list(state.get("sent", []))
            if isinstance(item, dict)
        }
        if message_key not in known_keys:
            state["pending"].append(_message_entry_from_channel(channel))
            state["last_enqueued_key"] = message_key

    state["generated_at"] = time.time()
    state["pending"] = list(state.get("pending", []))[-12:]
    state["sent"] = list(state.get("sent", []))[-20:]
    _save_json(CODEX_OUTBOX_PATH, state)
    return state


def enqueue_codex_implementation_request() -> dict:
    state = load_codex_outbox()
    request = save_codex_implementation_request()
    if request.get("status") != "ready_for_codex":
        _save_json(CODEX_OUTBOX_PATH, state)
        return state

    entry = _message_entry_from_implementation_request(request)
    message_key = str(entry.get("message_key", "")).strip()
    known_keys = {
        str(item.get("message_key", "")).strip()
        for item in list(state.get("pending", [])) + list(state.get("sent", []))
        if isinstance(item, dict)
    }
    if message_key and message_key not in known_keys:
        state["pending"].append(entry)
        state["last_enqueued_key"] = message_key

    state["generated_at"] = time.time()
    state["pending"] = list(state.get("pending", []))[-12:]
    _save_json(CODEX_OUTBOX_PATH, state)
    return state


def enqueue_current_codex_message() -> dict:
    state = load_codex_outbox()
    channel = load_codex_channel()
    message_key = str(channel.get("message_key", "")).strip()
    if not message_key:
        _save_json(CODEX_OUTBOX_PATH, state)
        return state

    known_keys = {
        str(item.get("message_key", "")).strip()
        for item in list(state.get("pending", [])) + list(state.get("sent", []))
        if isinstance(item, dict)
    }
    if message_key not in known_keys:
        state["pending"].append(_message_entry_from_channel(channel))
        state["last_enqueued_key"] = message_key

    state["generated_at"] = time.time()
    state["pending"] = list(state.get("pending", []))[-12:]
    _save_json(CODEX_OUTBOX_PATH, state)
    return state


def mark_next_codex_message_sent() -> dict:
    state = load_codex_outbox()
    pending = list(state.get("pending", []))
    if not pending:
        _save_json(CODEX_OUTBOX_PATH, state)
        return state

    item = pending.pop(0)
    item["status"] = "sent"
    item["sent_at"] = time.time()
    sent = list(state.get("sent", []))
    sent.append(item)

    state["pending"] = pending
    state["sent"] = sent[-20:]
    state["last_sent_key"] = str(item.get("message_key", "")).strip()
    state["generated_at"] = time.time()
    _save_json(CODEX_OUTBOX_PATH, state)
    return state


def clear_codex_outbox_pending() -> dict:
    state = load_codex_outbox()
    state["pending"] = []
    state["generated_at"] = time.time()
    _save_json(CODEX_OUTBOX_PATH, state)
    return state
