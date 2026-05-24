from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.command_schema import Command
from core.confirmation_flow import handle_pending_confirmation
from core.direct_response import is_confirmation_no, smart_open_choice_kind


@dataclass(frozen=True)
class DirectResponseState:
    pending_command: Command | None
    pending_command_learning_text: str
    pending_smart_open_choice: str | None
    pending_smart_open_invalid_attempts: int = 0
    direct_response_ready_announced: bool = False


@dataclass(frozen=True)
class DirectResponseResult:
    handled: bool
    state: DirectResponseState
    message: str = ""


def handle_direct_response_flow(
    user_input: str,
    state: DirectResponseState,
    *,
    execute_command: Callable[[Command], str],
    process_action: Callable[[dict], Command | str],
    remember_correction: Callable[[Command], None] | None = None,
    retry_invalid_smart_open: bool = True,
) -> DirectResponseResult:
    if state.pending_command is not None:
        confirmation_result = handle_pending_confirmation(
            user_input,
            state.pending_command,
            state.pending_command_learning_text,
            execute_command,
            remember_correction,
        )
        direct_ready = state.direct_response_ready_announced
        if confirmation_result.accepted or confirmation_result.cancelled:
            direct_ready = False
        return DirectResponseResult(
            handled=True,
            state=DirectResponseState(
                pending_command=confirmation_result.pending_command,
                pending_command_learning_text=confirmation_result.pending_learning_text,
                pending_smart_open_choice=state.pending_smart_open_choice,
                pending_smart_open_invalid_attempts=state.pending_smart_open_invalid_attempts,
                direct_response_ready_announced=direct_ready,
            ),
            message=confirmation_result.message,
        )

    if state.pending_smart_open_choice is None:
        return DirectResponseResult(handled=False, state=state)

    if is_confirmation_no(user_input):
        return DirectResponseResult(
            handled=True,
            state=DirectResponseState(
                pending_command=None,
                pending_command_learning_text=state.pending_command_learning_text,
                pending_smart_open_choice=None,
                pending_smart_open_invalid_attempts=0,
                direct_response_ready_announced=False,
            ),
            message="Ok, nao abri.",
        )

    kind = smart_open_choice_kind(user_input)
    if not kind:
        attempts = state.pending_smart_open_invalid_attempts + 1
        if retry_invalid_smart_open and attempts >= 2:
            return DirectResponseResult(
                handled=True,
                state=DirectResponseState(
                    pending_command=None,
                    pending_command_learning_text=state.pending_command_learning_text,
                    pending_smart_open_choice=None,
                    pending_smart_open_invalid_attempts=0,
                    direct_response_ready_announced=False,
                ),
                message="Nao consegui entender a resposta. Cancelei essa pergunta.",
            )
        return DirectResponseResult(
            handled=True,
            state=DirectResponseState(
                pending_command=None,
                pending_command_learning_text=state.pending_command_learning_text,
                pending_smart_open_choice=state.pending_smart_open_choice,
                pending_smart_open_invalid_attempts=attempts if retry_invalid_smart_open else state.pending_smart_open_invalid_attempts,
                direct_response_ready_announced=state.direct_response_ready_announced,
            ),
            message="Responda com app, site ou cancelar." if retry_invalid_smart_open else "Responda com 'app' ou 'site'.",
        )

    raw_action = {
        "intent": "smart_open_choice",
        "target": {
            "name": state.pending_smart_open_choice,
            "kind": kind,
        },
    }
    processed = process_action(raw_action)
    if isinstance(processed, str):
        message = processed
    else:
        message = execute_command(processed)

    return DirectResponseResult(
        handled=True,
        state=DirectResponseState(
            pending_command=None,
            pending_command_learning_text=state.pending_command_learning_text,
            pending_smart_open_choice=None,
            pending_smart_open_invalid_attempts=0,
            direct_response_ready_announced=False,
        ),
        message=message,
    )
