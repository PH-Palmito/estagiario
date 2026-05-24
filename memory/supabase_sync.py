from __future__ import annotations

from datetime import UTC, datetime

import requests

from config import (
    SUPABASE_ANON_KEY,
    SUPABASE_MEMORY_TABLE,
    SUPABASE_PUBLISHABLE_KEY,
    SUPABASE_REST_URL,
    SUPABASE_SYNC_ENABLED,
    join_url,
)


def _active_api_key() -> str:
    return SUPABASE_ANON_KEY or SUPABASE_PUBLISHABLE_KEY


def supabase_sync_ready() -> bool:
    return bool(SUPABASE_SYNC_ENABLED and SUPABASE_REST_URL and _active_api_key())


def _headers(prefer_upsert: bool = False) -> dict[str, str]:
    api_key = _active_api_key()
    headers = {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if prefer_upsert:
        headers["Prefer"] = "resolution=merge-duplicates,return=minimal"
    return headers


def _table_url() -> str:
    return join_url(SUPABASE_REST_URL, SUPABASE_MEMORY_TABLE)


def upsert_memory_state(key: str, payload: dict, category: str = "state", timeout_seconds: int = 8) -> bool:
    if not supabase_sync_ready() or not key:
        return False

    row = {
        "key": str(key).strip(),
        "category": str(category or "state").strip() or "state",
        "payload": payload if isinstance(payload, dict) else {"value": payload},
        "updated_at": datetime.now(UTC).isoformat(),
    }

    response = requests.post(
        _table_url(),
        params={"on_conflict": "key"},
        headers=_headers(prefer_upsert=True),
        json=row,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return True


def fetch_memory_state(key: str, timeout_seconds: int = 8) -> dict | None:
    if not supabase_sync_ready() or not key:
        return None

    response = requests.get(
        _table_url(),
        params={
            "select": "key,category,payload,updated_at",
            "key": f"eq.{str(key).strip()}",
            "limit": "1",
        },
        headers=_headers(),
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list) or not data:
        return None
    item = data[0]
    return item if isinstance(item, dict) else None


def fetch_memory_payload(key: str, timeout_seconds: int = 8) -> dict | None:
    row = fetch_memory_state(key=key, timeout_seconds=timeout_seconds)
    if not isinstance(row, dict):
        return None
    payload = row.get("payload")
    return payload if isinstance(payload, dict) else None


def fetch_memory_payload_safely(key: str, timeout_seconds: int = 8) -> dict | None:
    try:
        return fetch_memory_payload(key=key, timeout_seconds=timeout_seconds)
    except Exception:
        return None


def sync_memory_state_safely(key: str, payload: dict, category: str = "state") -> bool:
    try:
        return upsert_memory_state(key=key, payload=payload, category=category)
    except Exception:
        return False
