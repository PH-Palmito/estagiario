import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
EXECUTION_LOG_PATH = MEMORY_DIR / "execution_log.jsonl"


def _coerce(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _coerce(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_coerce(item) for item in value]
    return str(value)


def append_execution_log(event_type: str, payload: dict | None = None):
    entry = {
        "ts": time.time(),
        "event": str(event_type or "").strip() or "unknown",
        "data": _coerce(payload or {}),
    }

    line = json.dumps(entry, ensure_ascii=False) + "\n"
    EXECUTION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EXECUTION_LOG_PATH, "a", encoding="utf-8") as handle:
        handle.write(line)


def clear_execution_log():
    try:
        os.remove(EXECUTION_LOG_PATH)
    except FileNotFoundError:
        pass
