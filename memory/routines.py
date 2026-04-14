import json
from pathlib import Path


FILE = Path("memory/routines.json")


def load_routines():
    if not FILE.exists():
        return {}

    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

    if not isinstance(data, dict):
        return {}

    return data


def get_routine(name: str):
    routines = load_routines()
    return routines.get(name.lower().strip())


def list_routines():
    return list(load_routines().keys())
