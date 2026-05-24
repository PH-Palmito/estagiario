from __future__ import annotations

import json
from pathlib import Path

from memory.obsidian_sync import sync_knowledge_vault, sync_profile_note
from memory.profile import load_profile

ROOT = Path(__file__).resolve().parents[1]
DIRECTIVES_PATH = ROOT / "memory" / "axel_directives.json"


def load_axel_directives() -> dict:
    try:
        data = json.loads(DIRECTIVES_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def bootstrap_obsidian_knowledge() -> bool:
    profile = load_profile() or {}
    directives = load_axel_directives() or {}
    profile_ok = sync_profile_note(profile) if profile else True
    knowledge_ok = sync_knowledge_vault(profile_payload=profile, directives_payload=directives)
    return bool(profile_ok and knowledge_ok)
