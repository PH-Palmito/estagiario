import json
import os
import time
from pathlib import Path


HISTORY_PATH = Path("memory/vision_history.json")
MAX_ITEMS = 8


def _load_history() -> list[dict]:
    try:
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data if isinstance(data, list) else []


def _save_history(items: list[dict]):
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(items[-MAX_ITEMS:], ensure_ascii=False, indent=2)
    tmp_path = HISTORY_PATH.with_name(f"{HISTORY_PATH.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(payload, encoding="utf-8")
    os.replace(tmp_path, HISTORY_PATH)


def remember_vision_analysis(source: str, summary: str, details: dict | None = None):
    summary = " ".join(str(summary or "").split()).strip()
    if not summary:
        return
    details = details if isinstance(details, dict) else {}
    items = _load_history()
    items.append(
        {
            "created_at": time.time(),
            "source": str(source or "imagem"),
            "summary": summary,
            "details": details,
        }
    )
    _save_history(items)


def last_vision_analysis() -> str:
    items = _load_history()
    if not items:
        return "Ainda não tenho análise visual guardada."
    item = items[-1]
    source = str(item.get("source", "imagem")).strip() or "imagem"
    summary = str(item.get("summary", "")).strip()
    if not summary:
        return "A última análise visual ficou vazia."
    return f"Última análise visual ({source}): {summary}"


def last_vision_item() -> dict | None:
    items = _load_history()
    if not items:
        return None
    item = items[-1]
    return item if isinstance(item, dict) else None
