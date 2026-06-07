from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

_LOCKS: dict[Path, threading.RLock] = {}
_LOCKS_GUARD = threading.Lock()
REPLACE_RETRY_ATTEMPTS = 8
REPLACE_RETRY_DELAY_SECONDS = 0.025
MISSING_TMP_RETRY_ATTEMPTS = 3


def _lock_for(path: Path) -> threading.RLock:
    resolved = path.resolve()
    with _LOCKS_GUARD:
        lock = _LOCKS.get(resolved)
        if lock is None:
            lock = threading.RLock()
            _LOCKS[resolved] = lock
        return lock


class JsonStorage(Protocol):
    def read(self, path: Path, default: Any, *, validator: Callable[[Any], bool] | None = None) -> Any:
        ...

    def write(self, path: Path, payload: Any, *, indent: int | None = 2, trailing_newline: bool = False) -> None:
        ...

    def update(
        self,
        path: Path,
        default: Any,
        updater: Callable[[Any], Any],
        *,
        validator: Callable[[Any], bool] | None = None,
        indent: int | None = 2,
        trailing_newline: bool = False,
    ) -> Any:
        ...


@dataclass(frozen=True)
class LocalJsonStorage:
    """Atomic JSON storage backend for local files."""

    def _replace_with_retry(self, tmp_path: Path, path: Path) -> None:
        last_error: PermissionError | None = None
        for attempt in range(REPLACE_RETRY_ATTEMPTS):
            try:
                os.replace(tmp_path, path)
                return
            except PermissionError as exc:
                last_error = exc
                time.sleep(REPLACE_RETRY_DELAY_SECONDS * (attempt + 1))
        try:
            tmp_path.unlink(missing_ok=True)
        except Exception:
            pass
        if last_error:
            raise last_error

    def read(self, path: Path, default: Any, *, validator: Callable[[Any], bool] | None = None) -> Any:
        with _lock_for(path):
            if not path.exists():
                return default
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                return default
            if validator is not None and not validator(data):
                return default
            return data

    def write(self, path: Path, payload: Any, *, indent: int | None = 2, trailing_newline: bool = False) -> None:
        with _lock_for(path):
            path.parent.mkdir(parents=True, exist_ok=True)
            content = json.dumps(payload, ensure_ascii=False, indent=indent)
            if trailing_newline:
                content += "\n"
            last_missing: FileNotFoundError | None = None
            for attempt in range(MISSING_TMP_RETRY_ATTEMPTS):
                tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
                tmp_path.write_text(content, encoding="utf-8")
                try:
                    self._replace_with_retry(tmp_path, path)
                    return
                except FileNotFoundError as exc:
                    last_missing = exc
                    time.sleep(REPLACE_RETRY_DELAY_SECONDS * (attempt + 1))
            if last_missing:
                raise last_missing

    def update(
        self,
        path: Path,
        default: Any,
        updater: Callable[[Any], Any],
        *,
        validator: Callable[[Any], bool] | None = None,
        indent: int | None = 2,
        trailing_newline: bool = False,
    ) -> Any:
        with _lock_for(path):
            current = self.read(path, default, validator=validator)
            updated = updater(current)
            self.write(path, updated, indent=indent, trailing_newline=trailing_newline)
            return updated


DEFAULT_JSON_STORAGE: JsonStorage = LocalJsonStorage()


def read_json_file(path: Path, default: Any, *, validator: Callable[[Any], bool] | None = None) -> Any:
    return DEFAULT_JSON_STORAGE.read(path, default, validator=validator)


def write_json_atomic(path: Path, payload: Any, *, indent: int | None = 2, trailing_newline: bool = False) -> None:
    DEFAULT_JSON_STORAGE.write(path, payload, indent=indent, trailing_newline=trailing_newline)


def update_json_file(
    path: Path,
    default: Any,
    updater: Callable[[Any], Any],
    *,
    validator: Callable[[Any], bool] | None = None,
    indent: int | None = 2,
    trailing_newline: bool = False,
) -> Any:
    return DEFAULT_JSON_STORAGE.update(
        path,
        default,
        updater,
        validator=validator,
        indent=indent,
        trailing_newline=trailing_newline,
    )
