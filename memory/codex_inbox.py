import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
CODEX_INBOX_PATH = MEMORY_DIR / "codex_inbox.json"
CODEX_OUTBOX_PATH = MEMORY_DIR / "codex_outbox.json"


def _save_json(path: Path, payload: dict):
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    last_error = None
    for attempt in range(4):
        tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
        tmp_path.write_text(content, encoding="utf-8")
        try:
            os.replace(tmp_path, path)
            return
        except PermissionError as exc:
            last_error = exc
            try:
                tmp_path.unlink(missing_ok=True)
            except Exception:
                pass
            time.sleep(0.05 * (attempt + 1))
    if last_error:
        raise last_error


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _default_state() -> dict:
    return {
        "generated_at": time.time(),
        "items": [],
        "last_reply_at": 0.0,
        "last_reply_kind": "",
    }


def load_codex_inbox() -> dict:
    data = _load_json(CODEX_INBOX_PATH)
    if isinstance(data, dict):
        base = _default_state()
        base.update(data)
        if not isinstance(base.get("items"), list):
            base["items"] = []
        return base
    return _default_state()


def _latest_sent_message_key() -> str:
    outbox = _load_json(CODEX_OUTBOX_PATH)
    sent = outbox.get("sent") if isinstance(outbox.get("sent"), list) else []
    if sent:
        latest = sent[-1] if isinstance(sent[-1], dict) else {}
        return str(latest.get("message_key", "")).strip()
    return str(outbox.get("last_sent_key", "")).strip()


def add_codex_inbox_item(kind: str, text: str) -> dict:
    content = str(text or "").strip()
    reply_kind = str(kind or "reply").strip().lower() or "reply"
    state = load_codex_inbox()
    if not content:
        _save_json(CODEX_INBOX_PATH, state)
        return state

    state["items"].append(
        {
            "kind": reply_kind,
            "text": content,
            "message_key": _latest_sent_message_key(),
            "at": time.time(),
        }
    )
    state["items"] = list(state.get("items", []))[-20:]
    state["last_reply_at"] = time.time()
    state["last_reply_kind"] = reply_kind
    state["generated_at"] = time.time()
    _save_json(CODEX_INBOX_PATH, state)
    return state


def clear_codex_inbox() -> dict:
    state = _default_state()
    _save_json(CODEX_INBOX_PATH, state)
    return state


def latest_codex_inbox_item(*kinds: str) -> dict:
    state = load_codex_inbox()
    items = state.get("items") or []
    allowed = {str(kind).strip().lower() for kind in kinds if str(kind).strip()}
    for item in reversed(items):
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "")).strip().lower()
        if allowed and kind not in allowed:
            continue
        return item
    return {}
