from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class StartupFlowHandlers:
    handle_startup_cli: Callable[[object], bool]
    initialize_runtime_services: Callable[[bool], None]
    announce_voice_startup: Callable[..., None]
    refresh_ui_runtime_state: Callable[[], None]
    send_startup_briefing: Callable[[bool], bool] | None = None


def run_startup_flow(
    *,
    flags: object,
    voice_mode: bool,
    hotword_mode: bool,
    ui_mode: bool,
    defer_startup_briefing: bool,
    handlers: StartupFlowHandlers,
) -> bool:
    if handlers.handle_startup_cli(flags):
        return False

    handlers.initialize_runtime_services(ui_mode)

    if voice_mode:
        handlers.announce_voice_startup(
            hotword_mode=hotword_mode,
            defer_startup_briefing=defer_startup_briefing,
        )
    elif handlers.send_startup_briefing and (ui_mode or bool(getattr(flags, "startup_mode", False))):
        handlers.send_startup_briefing(False)

    handlers.refresh_ui_runtime_state()
    return True
