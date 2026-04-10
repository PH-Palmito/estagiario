import json
from pathlib import Path


FILE = Path("memory/aliases.json")


def load_aliases():
    if not FILE.exists():
        return {}

    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _normalized_aliases():
    raw = load_aliases()
    return {str(key).lower(): value for key, value in raw.items()}


def resolve_alias(name: str):
    aliases = _normalized_aliases()
    value = aliases.get(name.lower())

    if isinstance(value, str):
        return value

    if isinstance(value, dict) and value.get("type") in {"file", "path"}:
        target = value.get("target")
        return target if isinstance(target, str) else None

    return None


def load_app_aliases():
    aliases = {}

    for key, value in _normalized_aliases().items():
        if isinstance(value, dict) and value.get("type") == "app":
            target = value.get("target")
            if isinstance(target, str) and target.strip():
                aliases[key] = target.strip().lower()

    return aliases


def load_site_aliases():
    aliases = {}

    for key, value in _normalized_aliases().items():
        if isinstance(value, dict) and value.get("type") == "site":
            target = value.get("target")
            if isinstance(target, str) and target.strip():
                aliases[key] = target.strip()

    return aliases
