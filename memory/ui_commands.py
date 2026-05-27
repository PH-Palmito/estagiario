import time
from pathlib import Path

from memory.json_store import read_json_file, update_json_file, write_json_atomic

QUEUE_PATH = Path(__file__).with_name("ui_commands.json")


def _load_queue() -> list[dict]:
    data = read_json_file(QUEUE_PATH, [], validator=lambda value: isinstance(value, list))
    return [item for item in data if isinstance(item, dict)]


def _save_queue(queue: list[dict]):
    write_json_atomic(QUEUE_PATH, queue, indent=2)


def enqueue_ui_command(text: str, source: str = "hud", silent: bool = False):
    content = str(text or "").strip()
    if not content:
        return

    def append_item(queue: list[dict]) -> list[dict]:
        clean_queue = [item for item in queue if isinstance(item, dict)]
        clean_queue.append({
            "text": content,
            "source": source,
            "silent": bool(silent),
            "created_at": time.time(),
        })
        return clean_queue[-20:]

    update_json_file(
        QUEUE_PATH,
        [],
        append_item,
        validator=lambda value: isinstance(value, list),
        indent=2,
    )


def dequeue_ui_command_item() -> dict:
    selected = {}

    def pop_item(queue: list[dict]) -> list[dict]:
        nonlocal selected
        clean_queue = [item for item in queue if isinstance(item, dict)]
        if not clean_queue:
            selected = {}
            return []
        selected = clean_queue.pop(0)
        return clean_queue

    update_json_file(
        QUEUE_PATH,
        [],
        pop_item,
        validator=lambda value: isinstance(value, list),
        indent=2,
    )
    return selected


def dequeue_ui_command() -> str:
    item = dequeue_ui_command_item()
    if not item:
        return ""
    return str(item.get("text", "")).strip()
