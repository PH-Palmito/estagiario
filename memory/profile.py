import json
from pathlib import Path

from memory.obsidian_sync import sync_knowledge_vault, sync_profile_note
from memory.supabase_sync import fetch_memory_payload_safely, sync_memory_state_safely

PROFILE_PATH = Path("memory/profile.json")


def load_profile():
    if PROFILE_PATH.exists():
        try:
            with open(PROFILE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            pass

    remote = fetch_memory_payload_safely("profile")
    if isinstance(remote, dict):
        save_profile(remote)
        return remote
    return {}


def save_profile(data):
    payload = dict(data or {})
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
    sync_memory_state_safely("profile", payload, category="profile")
    sync_profile_note(payload)
    sync_knowledge_vault(profile_payload=payload)


def set_value(key, value):
    data = load_profile()
    data[key] = value
    save_profile(data)


def get_value(key):
    data = load_profile()
    return data.get(key)
