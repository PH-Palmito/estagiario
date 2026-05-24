import json
import os
import time
from pathlib import Path

from memory.codex_channel import load_codex_channel

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
CODEX_NOTIFICATIONS_PATH = MEMORY_DIR / "codex_notifications.json"


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


def load_codex_notifications() -> dict:
    data = _load_json(CODEX_NOTIFICATIONS_PATH)
    if isinstance(data, dict):
        return data
    return {"last_suggested_key": "", "last_suggested_at": 0.0}


def consume_codex_suggestion() -> str:
    channel = load_codex_channel()
    if not bool(channel.get("should_notify")):
        return ""

    message_key = str(channel.get("message_key", "")).strip()
    title = str(channel.get("title", "")).strip()
    reason = str(channel.get("notify_reason", "")).strip()
    next_action = str(channel.get("next_action", "")).strip()
    urgency = str(channel.get("urgency", "")).strip()

    state = load_codex_notifications()
    if message_key and state.get("last_suggested_key") == message_key:
        return ""

    payload = {
        "last_suggested_key": message_key,
        "last_suggested_at": time.time(),
    }
    _save_json(CODEX_NOTIFICATIONS_PATH, payload)

    base = f"Axel recomenda acionar o Codex agora para: {title}."
    if reason:
        base += f" Motivo: {reason}."
    if urgency:
        base += f" Urgencia: {urgency}."
    if next_action:
        base += f" Proxima acao: {next_action}."
    return base


def reset_codex_suggestion_memory() -> dict:
    payload = {"last_suggested_key": "", "last_suggested_at": 0.0}
    _save_json(CODEX_NOTIFICATIONS_PATH, payload)
    return payload
