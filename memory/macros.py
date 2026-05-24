import json
from pathlib import Path

FILE = Path("memory/macros.json")


def load_macros():
    if not FILE.exists():
        return {}

    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_macros(macros):
    FILE.write_text(
        json.dumps(macros, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def add_macro(name, steps):
    macros = load_macros()
    macros[name.lower()] = steps
    save_macros(macros)


def get_macro(name):
    macros = load_macros()
    return macros.get(name.lower())


def list_macros():
    return list(load_macros().keys())


def delete_macro(name):
    macros = load_macros()
    key = name.lower()

    if key not in macros:
        return False

    del macros[key]
    save_macros(macros)
    return True