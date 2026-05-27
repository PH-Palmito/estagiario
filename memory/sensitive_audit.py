from __future__ import annotations

import json
import time
from pathlib import Path

SENSITIVE_ACTION_AUDIT_PATH = Path("memory") / "sensitive_action_audit.jsonl"
MAX_AUDIT_LINES = 500


def _coerce(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _coerce(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_coerce(item) for item in value]
    return str(value)


def append_sensitive_action_audit(event_type: str, payload: dict | None = None, *, path: Path | None = None) -> None:
    target = path or SENSITIVE_ACTION_AUDIT_PATH
    entry = {
        "ts": time.time(),
        "event": str(event_type or "").strip() or "unknown",
        "data": _coerce(payload or {}),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    if target.exists():
        try:
            lines = target.read_text(encoding="utf-8").splitlines()[-(MAX_AUDIT_LINES - 1) :]
        except Exception:
            lines = []
    lines.append(json.dumps(entry, ensure_ascii=False))
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
