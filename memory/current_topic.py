import json
import time
from pathlib import Path

from memory.json_store import read_json_file, write_json_atomic
from memory.obsidian_sync import sync_current_topic_note
from memory.supabase_sync import fetch_memory_payload_safely, sync_memory_state_safely

TOPIC_PATH = Path("memory/current_topic.json")


def _fingerprint(payload: dict) -> str:
    stable = dict(payload or {})
    stable.pop("updated_at", None)
    return json.dumps(stable, ensure_ascii=False, sort_keys=True)


def _save(payload: dict):
    write_json_atomic(TOPIC_PATH, payload, indent=2)


def load_current_topic() -> dict:
    data = read_json_file(TOPIC_PATH, {}, validator=lambda value: isinstance(value, dict))
    if data:
        return data

    remote = fetch_memory_payload_safely("current_topic")
    if isinstance(remote, dict):
        _save(remote)
        return remote
    return {}


def save_current_topic(payload: dict) -> dict:
    data = dict(payload or {})
    current = load_current_topic()
    if current and _fingerprint(current) == _fingerprint(data):
        return current
    data["updated_at"] = time.time()
    _save(data)
    sync_memory_state_safely("current_topic", data, category="conversation")
    sync_current_topic_note(data)
    return data


def update_current_topic_from_vision(summary: str, details: dict | None = None, source: str = "screen") -> dict:
    details = details if isinstance(details, dict) else {}
    payload = {
        "topic": str(details.get("page_title", "")).strip() or str(summary or "").strip()[:180],
        "summary": str(summary or "").strip(),
        "source": str(source or "screen").strip() or "screen",
        "page_title": str(details.get("page_title", "")).strip(),
        "page_url": str(details.get("page_url", "")).strip(),
        "lines": list(details.get("lines") or [])[:10],
    }
    return save_current_topic(payload)


def update_current_topic_from_conversation(
    user_input: str,
    assistant_response: str,
    *,
    topic: str = "",
    source: str = "conversation",
    related_title: str = "",
    related_summary: str = "",
    keywords: list[str] | None = None,
) -> dict:
    current = load_current_topic()
    normalized_topic = str(topic or "").strip() or str(current.get("topic", "")).strip() or str(user_input or "").strip()[:180]
    current_topic_name = str(current.get("topic", "")).strip()
    topic_changed = bool(normalized_topic and current_topic_name and normalized_topic != current_topic_name)
    inherited_summary = "" if topic_changed else str(current.get("summary", "") or "").strip()
    inherited_title = "" if topic_changed else str(current.get("page_title", "") or "").strip()
    inherited_url = "" if topic_changed else str(current.get("page_url", "") or "").strip()
    inherited_lines = [] if topic_changed else list(current.get("lines") or [])[:10]
    inherited_keywords = [] if topic_changed else [str(item).strip() for item in (current.get("keywords") or []) if str(item).strip()]
    payload = {
        "topic": normalized_topic,
        "summary": str(related_summary or inherited_summary or "").strip(),
        "source": str(source or "conversation").strip() or "conversation",
        "page_title": str(related_title or inherited_title or "").strip(),
        "page_url": inherited_url,
        "lines": inherited_lines,
        "last_user_question": str(user_input or "").strip(),
        "last_assistant_answer": str(assistant_response or "").strip(),
        "keywords": [str(item).strip() for item in (keywords or inherited_keywords or []) if str(item).strip()][:8],
    }
    return save_current_topic(payload)
