from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.runtime_state import RuntimeState
from core.terminal_voice_io import TerminalVoiceIO


@dataclass
class AppRuntime:
    ui_history_max_items: int = 40
    runtime_state: RuntimeState = field(default_factory=RuntimeState)
    terminal_io: TerminalVoiceIO = field(init=False)
    ui_runtime: Any = None
    improvement_brain: Any = None
    reminder_announcer: Any = None
    response_pipeline: Any = None

    def __post_init__(self) -> None:
        self.terminal_io = TerminalVoiceIO(ui_history_max_items=self.ui_history_max_items)
