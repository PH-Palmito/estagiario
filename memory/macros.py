from pathlib import Path

from memory.json_store import read_json_file, update_json_file, write_json_atomic

FILE = Path("memory/macros.json")


def load_macros():
    return read_json_file(FILE, {}, validator=lambda value: isinstance(value, dict))


def save_macros(macros):
    write_json_atomic(FILE, macros, indent=2)


def add_macro(name, steps):
    update_json_file(
        FILE,
        {},
        lambda macros: {**dict(macros or {}), name.lower(): steps},
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )


def get_macro(name):
    macros = load_macros()
    return macros.get(name.lower())


def list_macros():
    return list(load_macros().keys())


def delete_macro(name):
    key = name.lower()
    if key not in load_macros():
        return False

    update_json_file(
        FILE,
        {},
        lambda macros: {item_key: value for item_key, value in dict(macros or {}).items() if item_key != key},
        validator=lambda value: isinstance(value, dict),
        indent=2,
    )
    return True
