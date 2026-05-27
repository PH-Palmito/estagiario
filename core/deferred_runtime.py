from __future__ import annotations

import threading
from collections.abc import Callable


def run_deferred(
    name: str,
    task: Callable[[], None],
    *,
    log_event: Callable[..., None] | None = None,
) -> threading.Thread:
    def runner() -> None:
        try:
            task()
            if log_event is not None:
                log_event("deferred_task_completed", name=name)
        except Exception as exc:
            if log_event is not None:
                log_event("deferred_task_failed", name=name, error=str(exc))

    thread = threading.Thread(target=runner, name=f"axel-{name}", daemon=True)
    thread.start()
    return thread
