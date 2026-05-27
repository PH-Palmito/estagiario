from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from memory.json_store import read_json_file, update_json_file, write_json_atomic

MEMORY_PATH = Path(__file__).resolve().parent / "action_memory.json"


def _load() -> dict[str, Any]:
    return read_json_file(MEMORY_PATH, {}, validator=lambda value: isinstance(value, dict))


def _save(payload: dict[str, Any]) -> None:
    write_json_atomic(MEMORY_PATH, payload, indent=2, trailing_newline=True)


def remember_memory(namespace: str, key: str, value: Any, tags: list[str] | None = None) -> dict[str, Any]:
    namespace = str(namespace or "general").strip() or "general"
    key = str(key or "").strip()
    if not key:
        return {"ok": False, "error": "Chave vazia."}

    item = {
        "value": value,
        "tags": [str(tag) for tag in (tags or []) if str(tag).strip()],
        "updated_at": time.time(),
    }

    def write_item(data: dict[str, Any]) -> dict[str, Any]:
        bucket = data.setdefault(namespace, {})
        bucket[key] = item
        return data

    update_json_file(
        MEMORY_PATH,
        {},
        write_item,
        validator=lambda loaded: isinstance(loaded, dict),
        indent=2,
        trailing_newline=True,
    )
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
