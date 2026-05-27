from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class MainLoopHandlers:
    maybe_announce_due_reminders: Callable[[bool], None]
    read_next_turn_input: Callable[..., object]
    handle_voice_cycle_break: Callable[[object], bool]
    handle_keyboard_interrupt: Callable[[], None]
    is_transcription_artifact: Callable[[str], bool]
    handle_user_turn: Callable[..., bool]


def run_main_loop(
    *,
    voice_mode: bool,
    hotword_mode: bool,
    handlers: MainLoopHandlers,
    voice_paused: bool = False,
) -> None:
    while True:
        handlers.maybe_announce_due_reminders(voice_mode)

        try:
            voice_cycle = handlers.read_next_turn_input(
                voice_mode=voice_mode,
                hotword_mode=hotword_mode,
                voice_paused=voice_paused,
            )
            user_input = voice_cycle.user_input
            queued_user_input = voice_cycle.queued_user_input
            voice_paused = voice_cycle.voice_paused
            if handlers.handle_voice_cycle_break(voice_cycle):
                break
        except KeyboardInterrupt:
            handlers.handle_keyboard_interrupt()
            break

        if not user_input:
            continue

        if handlers.is_transcription_artifact(user_input):
            continue

        handlers.handle_user_turn(
            user_input,
            queued_user_input=queued_user_input,
            voice_mode=voice_mode,
            hotword_mode=hotword_mode,
        )
