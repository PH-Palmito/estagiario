from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

MEMORY_PATH = Path(__file__).resolve().parent / "action_memory.json"


def _load() -> dict[str, Any]:
    try:
        data = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(payload: dict[str, Any]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = MEMORY_PATH.with_name(f"{MEMORY_PATH.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, MEMORY_PATH)


def remember_memory(namespace: str, key: str, value: Any, tags: list[str] | None = None) -> dict[str, Any]:
    namespace = str(namespace or "general").strip() or "general"
    key = str(key or "").strip()
    if not key:
        return {"ok": False, "error": "Chave vazia."}

    data = _load()
    bucket = data.setdefault(namespace, {})
    bucket[key] = {
        "value": value,
        "tags": [str(tag) for tag in (tags or []) if str(tag).strip()],
        "updated_at": time.time(),
    }
    _save(data)
    return {"ok": True, "namespace": namespace, "key": key}


def recall_memory(namespace: str, key: str) -> dict[str, Any]:
    namespace = str(namespace or "general").strip() or "general"
    key = str(key or "").strip()
    item = (_load().get(namespace) or {}).get(key)
    if not item:
        return {"ok": False, "namespace": namespace, "key": key, "error": "Memoria nao encontrada."}
    return {"ok": True, "namespace": namespace, "key": key, "item": item}


def list_memory_entries(namespace: str) -> dict[str, Any]:
    namespace = str(namespace or "general").strip() or "general"
    bucket = _load().get(namespace) or {}
    return {
        "ok": True,
        "namespace": namespace,
        "keys": sorted(bucket.keys()),
        "count": len(bucket),
    }
