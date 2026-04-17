import json
import re
import unicodedata
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


def _strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def normalize_alias_key(text: str) -> str:
    text = _strip_accents(str(text or "").strip().lower())
    text = re.sub(r"[^\w\s.-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" .")


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
                aliases[normalize_alias_key(key)] = target.strip().lower()

    return aliases


def load_smart_app_aliases():
    candidates = {}

    def add_candidate(alias: str, value: dict):
        alias = normalize_alias_key(alias)
        if not alias:
            return

        candidates.setdefault(alias, []).append(value)

    for key, value in _normalized_aliases().items():
        if isinstance(value, dict) and value.get("type") in {"smart_app", "smart_preference"}:
            target = value.get("target")
            if isinstance(target, str) and target.strip():
                canonical_value = dict(value)
                canonical_value["_key"] = normalize_alias_key(key)

                add_candidate(key, canonical_value)

                label = value.get("label")
                if isinstance(label, str) and label.strip():
                    add_candidate(label, canonical_value)

                for alias in value.get("aliases", []):
                    if isinstance(alias, str):
                        add_candidate(alias, canonical_value)

    aliases = {}
    for alias, values in candidates.items():
        targets = {
            str(value.get("target", "")).strip().lower()
            for value in values
            if isinstance(value, dict)
        }
        if len(targets) == 1:
            aliases[alias] = values[0]

    return aliases


def load_site_aliases():
    aliases = {}

    for key, value in _normalized_aliases().items():
        if isinstance(value, dict) and value.get("type") == "site":
            target = value.get("target")
            if isinstance(target, str) and target.strip():
                aliases[normalize_alias_key(key)] = target.strip()

    return aliases
