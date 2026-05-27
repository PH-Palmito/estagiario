from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class TurnFlowHandlers:
    record_user_turn_start: Callable[..., None]
    handle_pre_route_command: Callable[..., bool]
    handle_interactive_command: Callable[..., bool]
    handle_direct_response_command: Callable[..., bool]
    normalize_user_command: Callable[..., tuple[str, str]]
    handle_macro_command: Callable[..., bool]
    handle_routed_command: Callable[..., bool]


def handle_user_turn(
    user_input: str,
    *,
    queued_user_input: str,
    voice_mode: bool,
    hotword_mode: bool,
    handlers: TurnFlowHandlers,
) -> bool:
    handlers.record_user_turn_start(
        user_input,
        queued_user_input=queued_user_input,
        voice_mode=voice_mode,
    )

    if handlers.handle_pre_route_command(user_input, voice_mode=voice_mode):
        return True

    if handlers.handle_interactive_command(user_input, voice_mode=voice_mode, hotword_mode=hotword_mode):
        return True

    if handlers.handle_direct_response_command(
        user_input,
        voice_mode=voice_mode,
        retry_invalid_smart_open=True,
    ):
        return True

    original_user_input, normalized_user_input = handlers.normalize_user_command(user_input, voice_mode=voice_mode)

    if handlers.handle_macro_command(normalized_user_input, voice_mode=voice_mode):
        return True

    if handlers.handle_direct_response_command(
        normalized_user_input,
        voice_mode=voice_mode,
        retry_invalid_smart_open=False,
    ):
        return True

    return handlers.handle_routed_command(
        user_input=normalized_user_input,
        original_user_input=original_user_input,
        voice_mode=voice_mode,
    )
