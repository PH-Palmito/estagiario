from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Lock, Thread
from time import time
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKGROUND_TASK_HISTORY_PATH = ROOT / "memory" / "background_tasks.jsonl"
DEFAULT_MAX_PERSISTED_HISTORY = 200


@dataclass(frozen=True)
class BackgroundTaskSnapshot:
    task_id: str
    name: str
    status: str
    created_at: float
    started_at: float | None
    finished_at: float | None
    message: str
    error: str

    @property
    def duration_ms(self) -> float | None:
        if self.started_at is None or self.finished_at is None:
            return None
        return round((self.finished_at - self.started_at) * 1000, 2)

    def as_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "message": self.message,
            "error": self.error,
        }


@dataclass
class _BackgroundTaskState:
    task_id: str
    name: str
    status: str
    created_at: float
    started_at: float | None = None
    finished_at: float | None = None
    message: str = ""
    error: str = ""

    def snapshot(self) -> BackgroundTaskSnapshot:
        return BackgroundTaskSnapshot(
            task_id=self.task_id,
            name=self.name,
            status=self.status,
            created_at=self.created_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            message=self.message,
            error=self.error,
        )


def _coerce_json(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _coerce_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_coerce_json(item) for item in value]
    return str(value)


def _read_recent_jsonl(path: Path, limit: int = 50) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, limit):]
    except Exception:
        return []
    entries = []
    for line in lines:
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            entries.append(item)
    return entries


def _trim_jsonl_file(path: Path, max_lines: int) -> None:
    if max_lines <= 0 or not path.exists():
        return
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return
    if len(lines) <= max_lines:
        return
    try:
        path.write_text("\n".join(lines[-max_lines:]) + "\n", encoding="utf-8")
    except OSError:
        return


class BackgroundTaskRunner:
    def __init__(
        self,
        *,
        max_history: int = 20,
        max_persisted_history: int = DEFAULT_MAX_PERSISTED_HISTORY,
        thread_factory: Callable[..., Any] = Thread,
        history_path: Path | None = BACKGROUND_TASK_HISTORY_PATH,
        notification_sink: Callable[[dict[str, Any]], Any] | None = None,
    ):
        self.max_history = max(1, int(max_history or 20))
        self.max_persisted_history = max(1, int(max_persisted_history or DEFAULT_MAX_PERSISTED_HISTORY))
        self.thread_factory = thread_factory
        self.history_path = history_path
        self.notification_sink = notification_sink
        self._lock = Lock()
        self._counter = 0
        self._tasks: dict[str, _BackgroundTaskState] = {}
        self._order: list[str] = []
        self._notifications: list[dict[str, Any]] = []

    def submit(self, name: str, func: Callable[[], Any]) -> str:
        task_name = str(name or "background_task").strip() or "background_task"
        with self._lock:
            self._counter += 1
            task_id = f"bg-{self._counter}"
            self._tasks[task_id] = _BackgroundTaskState(
                task_id=task_id,
                name=task_name,
                status="queued",
                created_at=time(),
            )
            self._order.append(task_id)
            self._trim_locked()

        thread = self.thread_factory(
            target=lambda: self._run_task(task_id, func),
            name=f"axel-{task_id}-{task_name}",
            daemon=True,
        )
        thread.start()
        return task_id

    def snapshot(self) -> list[dict[str, Any]]:
        with self._lock:
            return [self._tasks[task_id].snapshot().as_dict() for task_id in self._order if task_id in self._tasks]

    def summary(self) -> dict[str, Any]:
        tasks = self.snapshot()
        running = [task for task in tasks if task["status"] in {"queued", "running"}]
        failed = [task for task in tasks if task["status"] == "failed"]
        completed = [task for task in tasks if task["status"] == "succeeded"]
        latest = tasks[-1] if tasks else {}
        return {
            "total": len(tasks),
            "running": len(running),
            "failed": len(failed),
            "succeeded": len(completed),
            "latest": latest,
            "recent": tasks[-3:],
        }

    def latest_result(self) -> dict[str, Any]:
        tasks = self.snapshot()
        finished = [task for task in tasks if task["status"] in {"succeeded", "failed"}]
        if finished:
            return finished[-1]
        if self.history_path is None:
            return {}
        persisted = [
            item
            for item in _read_recent_jsonl(self.history_path)
            if item.get("status") in {"succeeded", "failed"}
        ]
        return persisted[-1] if persisted else {}

    def consume_notifications(self) -> list[dict[str, Any]]:
        with self._lock:
            notifications = list(self._notifications)
            self._notifications.clear()
            return notifications

    def _run_task(self, task_id: str, func: Callable[[], Any]) -> None:
        self._mark(task_id, status="running", started_at=time())
        try:
            result = func()
        except Exception as exc:
            self._mark(task_id, status="failed", finished_at=time(), error=str(exc), message=f"Falha: {exc}")
            self._persist_task(task_id)
            self._queue_notification(task_id)
            return
        self._mark(task_id, status="succeeded", finished_at=time(), message=str(result or "Concluido."))
        self._persist_task(task_id)
        self._queue_notification(task_id)

    def _mark(self, task_id: str, **updates: Any) -> None:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            for key, value in updates.items():
                setattr(task, key, value)

    def _trim_locked(self) -> None:
        while len(self._order) > self.max_history:
            task_id = self._order.pop(0)
            self._tasks.pop(task_id, None)

    def _queue_notification(self, task_id: str) -> None:
        notification: dict[str, Any] | None = None
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            snapshot = task.snapshot().as_dict()
            notification = {
                "event": "background_task_finished",
                "task_id": snapshot.get("task_id", ""),
                "name": snapshot.get("name", ""),
                "status": snapshot.get("status", ""),
                "duration_ms": snapshot.get("duration_ms"),
                "message": snapshot.get("message", ""),
                "error": snapshot.get("error", ""),
                "created_at": time(),
            }
            self._notifications.append(notification)
            self._notifications = self._notifications[-10:]
        if self.notification_sink:
            try:
                self.notification_sink(notification)
            except Exception:
                return

    def _persist_task(self, task_id: str) -> None:
        if self.history_path is None:
            return
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return
            payload = task.snapshot().as_dict()
        try:
            self.history_path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(_coerce_json(payload), ensure_ascii=False) + "\n"
            with self.history_path.open("a", encoding="utf-8") as handle:
                handle.write(line)
            _trim_jsonl_file(self.history_path, self.max_persisted_history)
        except OSError:
            return


def _default_notification_sink(notification: dict[str, Any]) -> bool:
    from services.background_notification_service import publish_background_notification

    return publish_background_notification(notification)


DEFAULT_BACKGROUND_TASK_RUNNER = BackgroundTaskRunner(notification_sink=_default_notification_sink)


def submit_background_task(name: str, func: Callable[[], Any]) -> str:
    return DEFAULT_BACKGROUND_TASK_RUNNER.submit(name, func)


def background_task_summary() -> dict[str, Any]:
    return DEFAULT_BACKGROUND_TASK_RUNNER.summary()


def latest_background_task_result() -> dict[str, Any]:
    return DEFAULT_BACKGROUND_TASK_RUNNER.latest_result()


def consume_background_notifications() -> list[dict[str, Any]]:
    return DEFAULT_BACKGROUND_TASK_RUNNER.consume_notifications()
