from __future__ import annotations

import traceback
from collections.abc import Callable, Sequence
from datetime import datetime
from pathlib import Path


def startup_diagnostics_enabled(argv: Sequence[str]) -> bool:
    return "--startup" in argv


def startup_log_path(repo_root: Path | None = None) -> Path:
    root = repo_root or Path(__file__).resolve().parents[1]
    return root / ".tmp" / "axel-startup.log"


def append_startup_log(message: str, log_path: Path | None = None) -> None:
    path = log_path or startup_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as file:
        file.write(f"[{timestamp}] {message}\n")


def run_with_startup_diagnostics(argv: Sequence[str], main_func: Callable[[], None]) -> None:
    if not startup_diagnostics_enabled(argv):
        main_func()
        return

    append_startup_log("Bootstrap do Axel iniciado.")
    try:
        main_func()
    except Exception:
        append_startup_log("Falha fatal durante o startup:\n" + traceback.format_exc().rstrip())
        raise
    append_startup_log("Bootstrap do Axel encerrado.")
