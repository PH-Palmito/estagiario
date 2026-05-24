from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.command_schema import Command
from core.confirmation import confirmation_instruction, is_confirmation_accepted, is_confirmation_rejected


@dataclass
class ConfirmationFlowResult:
    handled: bool
    pending_command: Command | None
    pending_learning_text: str
    message: str = ""
    accepted: bool = False
    cancelled: bool = False


def handle_pending_confirmation(
    user_input: str,
    pending_command: Command | None,
    pending_learning_text: str,
    execute_command: Callable[[Command], str],
    remember_correction: Callable[[Command], None] | None = None,
) -> ConfirmationFlowResult:
    if pending_command is None:
        return ConfirmationFlowResult(
            handled=False,
            pending_command=None,
            pending_learning_text=pending_learning_text,
        )

    if is_confirmation_accepted(user_input, pending_command):
        if remember_correction is not None:
            remember_correction(pending_command)
        result = execute_command(pending_command)
        return ConfirmationFlowResult(
            handled=True,
            pending_command=None,
            pending_learning_text="",
            message=result,
            accepted=True,
        )

    if is_confirmation_rejected(user_input):
        return ConfirmationFlowResult(
            handled=True,
            pending_command=None,
            pending_learning_text="",
            message="Acao cancelada.",
            cancelled=True,
        )

    return ConfirmationFlowResult(
        handled=True,
        pending_command=pending_command,
        pending_learning_text=pending_learning_text,
        message=confirmation_instruction(pending_command),
    )
