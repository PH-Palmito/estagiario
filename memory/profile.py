import json
from pathlib import Path

PROFILE_PATH = Path("memory/profile.json")


def load_profile():
    if not PROFILE_PATH.exists():
        return {}

    with open(PROFILE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def save_profile(data):
    with open(PROFILE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def set_value(key, value):
    data = load_profile()
    data[key] = value
    save_profile(data)


def get_value(key):
    data = load_profile()
    return data.get(key)