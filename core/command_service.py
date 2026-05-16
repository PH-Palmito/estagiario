from __future__ import annotations

import time
from typing import Callable

from core.command_schema import Command
from core.context_resolver import resolve_params
from core.normalizer import normalize_action
from core.validator import validate_command


LogEvent = Callable[..., None]


def process_raw_action(raw_action: dict, runtime_state, log_event: LogEvent) -> Command | str:
    if not isinstance(raw_action, dict):
        log_event("action_invalid", reason="raw_action_not_dict", raw_action=str(raw_action))
        return "Acao invalida."

    command = normalize_action(raw_action)
    command = resolve_params(command, runtime_state)
    log_event(
        "action_processed",
        intent=raw_action.get("intent"),
        action=getattr(command, "action", ""),
        params=getattr(command, "params", {}),
        source=getattr(command, "source", ""),
    )

    ok, error = validate_command(command)
    if not ok:
        log_event(
            "action_validation_failed",
            action=getattr(command, "action", ""),
            params=getattr(command, "params", {}),
            error=error,
        )
        return error

    return command


def execute_processed_command(
    command: Command,
    runtime_state,
    execute: Callable[[Command], str],
    log_event: LogEvent,
    progress_callback: Callable[[Command], None] | None = None,
    voice_mode: bool = False,
) -> str:
    if progress_callback is not None:
        progress_callback(command)

    started_at = time.time()
    log_event(
        "command_execute_start",
        action=getattr(command, "action", ""),
        params=getattr(command, "params", {}),
        voice_mode=voice_mode,
    )
    result = execute(command)
    runtime_state.update(command, result)
    log_event(
        "command_execute_end",
        action=getattr(command, "action", ""),
        params=getattr(command, "params", {}),
        result=result,
        voice_mode=voice_mode,
        duration_ms=round((time.time() - started_at) * 1000, 2),
    )
    return result
