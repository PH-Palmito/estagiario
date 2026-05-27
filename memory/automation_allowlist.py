from __future__ import annotations

from pathlib import Path

from memory.json_store import read_json_file, update_json_file

AUTOMATION_ALLOWLIST_PATH = Path("memory") / "automation_allowlist.json"


def _normalize_name(name: str) -> str:
    return " ".join(str(name or "").strip().lower().split())


def load_trusted_automations() -> list[str]:
    data = read_json_file(AUTOMATION_ALLOWLIST_PATH, [], validator=lambda value: isinstance(value, list))
    names = []
    for item in data:
        normalized = _normalize_name(str(item))
        if normalized and normalized not in names:
            names.append(normalized)
    return names


def is_trusted_automation(name: str) -> bool:
    normalized = _normalize_name(name)
    return bool(normalized and normalized in load_trusted_automations())


def add_trusted_automation(name: str) -> list[str]:
    normalized = _normalize_name(name)
    if not normalized:
        return load_trusted_automations()

    def updater(current):
        names = []
        for item in current or []:
            item_name = _normalize_name(str(item))
            if item_name and item_name not in names:
                names.append(item_name)
        if normalized not in names:
            names.append(normalized)
        return names

    return update_json_file(
        AUTOMATION_ALLOWLIST_PATH,
        [],
        updater,
        validator=lambda value: isinstance(value, list),
        indent=2,
    )


def remove_trusted_automation(name: str) -> bool:
    normalized = _normalize_name(name)
    if not normalized:
        return False

    changed = {"value": False}

    def updater(current):
        names = []
        for item in current or []:
            item_name = _normalize_name(str(item))
            if item_name and item_name != normalized and item_name not in names:
                names.append(item_name)
        changed["value"] = len(names) != len(load_trusted_automations())
        return names

    update_json_file(
        AUTOMATION_ALLOWLIST_PATH,
        [],
        updater,
        validator=lambda value: isinstance(value, list),
        indent=2,
    )
    return bool(changed["value"])
