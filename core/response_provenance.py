from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from threading import RLock
from time import time


_LOCK = RLock()
_CURRENT = {"started_at": 0.0, "models": [], "tools": [], "files": []}


def begin_response_provenance() -> None:
    with _LOCK:
        _CURRENT.clear()
        _CURRENT.update({"started_at": time(), "models": [], "tools": [], "files": []})


def _safe_file_names(params: dict | None) -> list[str]:
    payload = params if isinstance(params, dict) else {}
    values = []
    for key in ("path", "paths", "src", "dst", "file", "files"):
        value = payload.get(key)
        if isinstance(value, (list, tuple)):
            values.extend(value)
        elif value:
            values.append(value)
    names = []
    for value in values:
        name = Path(str(value)).name.strip()
        if name and name not in names:
            names.append(name[:120])
    return names[:10]


def record_tool_use(action: str, params: dict | None = None) -> None:
    name = str(action or "").strip()
    if not name or name in {"respond", "start_conversation", "stop_conversation"}:
        return
    with _LOCK:
        tools = _CURRENT.setdefault("tools", [])
        if name not in tools:
            tools.append(name)
        files = _CURRENT.setdefault("files", [])
        for file_name in _safe_file_names(params):
            if file_name not in files:
                files.append(file_name)


def record_model_use(*, provider: str, model: str, policy: str = "", success: bool = True, fallback_used: bool = False) -> None:
    item = {
        "provider": str(provider or "").strip() or "unknown",
        "model": str(model or "").strip() or "unknown",
        "policy": str(policy or "").strip(),
        "success": bool(success),
        "fallback_used": bool(fallback_used),
    }
    with _LOCK:
        _CURRENT.setdefault("models", []).append(item)
        _CURRENT["models"] = _CURRENT["models"][-4:]


def response_provenance_snapshot() -> dict:
    with _LOCK:
        return deepcopy(_CURRENT)
