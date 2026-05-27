from __future__ import annotations

import json
import shutil
import time
from dataclasses import dataclass
from pathlib import Path

from memory.json_store import write_json_atomic

CRITICAL_MEMORY_FILES = (
    "ui_state.json",
    "ui_commands.json",
    "voice_preferences.json",
    "voice_corrections.json",
    "tts_pronunciations.json",
    "training.json",
    "agenda.json",
    "reminders.json",
    "operational_context.json",
    "operational_memory.json",
    "long_memory.json",
    "action_memory.json",
    "current_topic.json",
    "vision_history.json",
    "macros.json",
    "assistant_phrase_state.json",
)


@dataclass(frozen=True)
class BackupResult:
    backup_dir: Path
    copied: list[str]
    skipped: list[str]
    manifest_path: Path


def memory_dir(root: Path | None = None) -> Path:
    return (root or Path(__file__).resolve().parents[1]) / "memory"


def backups_dir(root: Path | None = None) -> Path:
    return memory_dir(root) / "backups"


def _backup_name(now: float | None = None) -> str:
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now or time.time()))
    return f"memory-{timestamp}"


def create_memory_backup(root: Path | None = None, *, now: float | None = None) -> BackupResult:
    base = memory_dir(root)
    target_dir = backups_dir(root) / _backup_name(now)
    target_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[str] = []
    for filename in CRITICAL_MEMORY_FILES:
        source = base / filename
        if not source.exists() or not source.is_file():
            skipped.append(filename)
            continue
        destination = target_dir / filename
        shutil.copy2(source, destination)
        copied.append(filename)

    manifest = {
        "created_at": time.time(),
        "files": copied,
        "skipped": skipped,
    }
    manifest_path = target_dir / "manifest.json"
    write_json_atomic(manifest_path, manifest, indent=2, trailing_newline=True)
    return BackupResult(target_dir, copied, skipped, manifest_path)


def list_memory_backups(root: Path | None = None, *, limit: int = 10) -> list[dict]:
    root_dir = backups_dir(root)
    if not root_dir.exists():
        return []

    rows = []
    for item in root_dir.iterdir():
        if not item.is_dir():
            continue
        manifest_path = item / "manifest.json"
        manifest = {}
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}
        rows.append(
            {
                "name": item.name,
                "path": str(item),
                "files_count": len(manifest.get("files") or []),
                "created_at": manifest.get("created_at", 0),
            }
        )

    rows.sort(key=lambda row: str(row.get("name", "")), reverse=True)
    return rows[: max(1, int(limit))]


def latest_memory_backup(root: Path | None = None) -> dict | None:
    backups = list_memory_backups(root, limit=1)
    return backups[0] if backups else None


def restore_memory_file(filename: str, backup_name: str, root: Path | None = None) -> Path:
    if filename not in CRITICAL_MEMORY_FILES:
        raise ValueError(f"Arquivo fora da lista critica: {filename}")

    base = memory_dir(root)
    backup_root = backups_dir(root) / str(backup_name)
    source = backup_root / filename
    if not source.exists() or not source.is_file():
        raise FileNotFoundError(str(source))

    destination = base / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


def memory_backup_summary(root: Path | None = None) -> dict:
    latest = latest_memory_backup(root)
    count = len(list_memory_backups(root, limit=1000))
    return {
        "count": count,
        "latest": latest or {},
        "critical_files": len(CRITICAL_MEMORY_FILES),
    }
