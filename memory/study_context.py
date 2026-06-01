from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from memory.json_store import read_json_file, write_json_atomic

CONTEXT_PATH = Path(__file__).resolve().parent / "study_context.json"


def load_study_context() -> dict[str, Any]:
    return read_json_file(CONTEXT_PATH, {}, validator=lambda value: isinstance(value, dict))


def save_study_context(context: dict[str, Any]) -> None:
    payload = dict(context)
    payload["updated_at"] = time.time()
    write_json_atomic(CONTEXT_PATH, payload)


def clear_study_context() -> None:
    write_json_atomic(CONTEXT_PATH, {})
