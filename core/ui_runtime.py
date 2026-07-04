from __future__ import annotations

import sys
import time
from collections.abc import Callable
from pathlib import Path

from core.ui_bridge import UIBridge


class UIRuntimeService:
    def __init__(
        self,
        *,
        root_dir: Path,
        runtime_patch: Callable[[], dict],
        normalize_text: Callable[[str], str],
        route: Callable[[str], dict],
        process_action: Callable[[dict], object],
        training_snapshot: Callable[[], dict],
        dequeue_ui_command_item: Callable[[], dict | None],
        append_ui_history: Callable[..., None],
        history_max_items: int = 40,
        python_executable: str | None = None,
    ):
        self.root_dir = root_dir
        self.runtime_patch = runtime_patch
        self.normalize_text = normalize_text
        self.route = route
        self.process_action = process_action
        self.training_snapshot = training_snapshot
        self.dequeue_ui_command_item = dequeue_ui_command_item
        self.append_ui_history = append_ui_history
        self.history_max_items = history_max_items
        self.python_executable = python_executable or sys.executable
        self._bridge: UIBridge | None = None
        self.silent_command_active = False
        self.active_command_id = ""
        self.active_command_text = ""

    def bridge(self) -> UIBridge:
        if self._bridge is None:
            self._bridge = UIBridge(
                root_dir=self.root_dir,
                python_executable=self.python_executable,
                runtime_patch=self.runtime_patch,
                normalize_text=self.normalize_text,
                route=self.route,
                process_action=self.process_action,
                training_snapshot=self.training_snapshot,
            )
        return self._bridge

    def refresh_runtime_state(self, extra: dict | None = None) -> None:
        self.bridge().refresh_runtime_state(extra)

    def launch_hud(self) -> None:
        self.bridge().launch_hud()

    def show_hud(self) -> str:
        return self.bridge().show_hud()

    def hide_hud(self) -> str:
        return self.bridge().hide_hud()

    def show_map(self, map_request: dict | None = None) -> str:
        return self.bridge().show_map(map_request)

    def show_training(self) -> str:
        return self.bridge().show_training()

    def show_health(self) -> str:
        return self.bridge().show_health()

    def maybe_handle_command(self, user_input: str) -> str | None:
        return self.bridge().maybe_handle_command(user_input)

    def poll_text_command(self, *, refresh_runtime_state: Callable[[dict | None], None]) -> str:
        queued_item = self.dequeue_ui_command_item()
        if not queued_item:
            self.silent_command_active = False
            return ""

        queued = str(queued_item.get("text", "")).strip()
        if not queued:
            self.silent_command_active = False
            return ""

        self.silent_command_active = bool(queued_item.get("silent", False))
        self.active_command_id = str(queued_item.get("id") or "").strip()
        self.active_command_text = queued
        self.append_ui_history("user", queued, max_items=self.history_max_items)
        refresh_runtime_state({
            "last_heard": queued,
            "command_feedback": {
                "id": self.active_command_id,
                "command": queued,
                "status": "processing",
                "message": "Comando em processamento.",
                "at": time.time(),
            },
        })
        return queued

    def complete_active_command(self, message: str, *, status: str = "success") -> None:
        if not self.active_command_id:
            return
        self.refresh_runtime_state({
            "command_feedback": {
                "id": self.active_command_id,
                "command": self.active_command_text,
                "status": str(status or "success"),
                "message": str(message or "").strip()[:500],
                "at": time.time(),
            }
        })
        self.active_command_id = ""
        self.active_command_text = ""
