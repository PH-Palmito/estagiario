import json
import os
import time
from pathlib import Path

QUEUE_PATH = Path(__file__).with_name("ui_commands.json")


def _load_queue() -> list[dict]:
    if not QUEUE_PATH.exists():
        return []

    try:
        data = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    except Exception:
        pass
    return []


def _save_queue(queue: list[dict]):
    tmp_path = QUEUE_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, QUEUE_PATH)


def enqueue_ui_command(text: str, source: str = "hud", silent: bool = False):
    content = str(text or "").strip()
    if not content:
        return

    queue = _load_queue()
    queue.append({
        "text": content,
        "source": source,
        "silent": bool(silent),
        "created_at": time.time(),
    })
    _save_queue(queue[-20:])


def dequeue_ui_command_item() -> dict:
    queue = _load_queue()
    if not queue:
        return {}

    item = queue.pop(0)
    _save_queue(queue)
    return item


def dequeue_ui_command() -> str:
    item = dequeue_ui_command_item()
    if not item:
        return ""
    return str(item.get("text", "")).strip()
