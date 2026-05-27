from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Callable
from typing import Any

from core.assistant_state import AssistantState
from core.runtime_state import RuntimeState
from core.terminal_voice_io import TerminalVoiceIO


@dataclass
class AppRuntime:
    ui_history_max_items: int = 40
    runtime_state: RuntimeState = field(default_factory=RuntimeState)
    assistant_state: AssistantState = field(default_factory=AssistantState)
    terminal_io: TerminalVoiceIO = field(init=False)
    ui_runtime: Any = None
    improvement_brain: Any = None
    reminder_announcer: Any = None
    response_pipeline: Any = None

    def __post_init__(self) -> None:
        self.terminal_io = TerminalVoiceIO(ui_history_max_items=self.ui_history_max_items)


@dataclass(frozen=True)
class AssistantRunConfig:
    flags: Any
    voice_mode: bool
    hotword_mode: bool
    ui_mode: bool
    voice_paused: bool = False


@dataclass(frozen=True)
class AssistantRuntimeRunner:
    app_runtime: AppRuntime
    run_startup: Callable[..., bool]
    run_main_loop: Callable[..., None]

    def run(self, config: AssistantRunConfig) -> None:
        self.app_runtime.terminal_io.hotword_ui_enabled = config.voice_mode and config.hotword_mode

        should_continue = self.run_startup(
            flags=config.flags,
            voice_mode=config.voice_mode,
            hotword_mode=config.hotword_mode,
            ui_mode=config.ui_mode,
        )
        if not should_continue:
            return

        self.run_main_loop(
            voice_mode=config.voice_mode,
            hotword_mode=config.hotword_mode,
            voice_paused=config.voice_paused,
        )
