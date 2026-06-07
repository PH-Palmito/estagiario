import json
import os
import re
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
EXECUTION_LOG_PATH = MEMORY_DIR / "execution_log.jsonl"
REDACTED_VALUE = "[redacted]"
REDACTED_EMAIL = "[email]"
REDACTED_NUMBER = "[number]"

SENSITIVE_KEY_PARTS = {
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "auth_token",
    "bot_token",
    "secret",
    "client_secret",
    "password",
    "passwd",
    "senha",
    "authorization",
    "cookie",
    "session",
}

SENSITIVE_TEXT_PATTERNS = [
    (re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}"), f"Bearer {REDACTED_VALUE}"),
    (re.compile(r"(?i)\b(token|api[_-]?key|senha|password|secret)\s*[:=]\s*[^\s,;]+"), rf"\1={REDACTED_VALUE}"),
    (re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", flags=re.I), REDACTED_EMAIL),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), REDACTED_NUMBER),
    (re.compile(r"\b\d{11,}\b"), REDACTED_NUMBER),
]


def _is_sensitive_key(key: str) -> bool:
    normalized = re.sub(r"[^a-z0-9_]+", "_", str(key or "").strip().lower())
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def _redact_text(value: str) -> str:
    redacted = str(value or "")
    for pattern, replacement in SENSITIVE_TEXT_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _coerce(value, *, key: str = ""):
    if key and _is_sensitive_key(key):
        return REDACTED_VALUE
    if isinstance(value, str):
        return _redact_text(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(item_key): _coerce(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_coerce(item) for item in value]
    return _redact_text(str(value))


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
