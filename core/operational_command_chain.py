from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.approval_verification_commands import (
    maybe_handle_approval_gate_command,
    maybe_handle_verification_command,
)
from core.codex_commands import (
    maybe_handle_codex_channel_command,
    maybe_handle_codex_implementation_request_command,
    maybe_handle_codex_inbox_command,
    maybe_handle_codex_outbox_command,
)
from core.directives_commands import maybe_handle_directives_command
from core.evolution_commands import (
    maybe_handle_auto_advance_command,
    maybe_handle_bottleneck_command,
    maybe_handle_patch_proposal_command,
)
from core.handoff_commands import (
    maybe_handle_handoff_application_command,
    maybe_handle_handoff_retry_command,
    maybe_handle_handoff_validation_command,
    maybe_handle_implementation_handoff_command,
)
from core.memory_commands import (
    maybe_handle_long_memory_command,
    maybe_handle_operational_context_command,
)
from core.self_evolution_commands import maybe_handle_self_evolution_command
from core.supervised_execution_commands import (
    maybe_handle_action_candidate_command,
    maybe_handle_execution_package_command,
)


@dataclass(frozen=True)
class OperationalCommandResult:
    response: str
    refresh_improvement_brain: bool = False
    announce_codex_suggestion: bool = False


@dataclass(frozen=True)
class _OperationalHandler:
    handle: Callable[[str], str | None]
    refresh_improvement_brain: bool = True
    announce_codex_suggestion: bool = True


def _operational_handlers() -> tuple[_OperationalHandler, ...]:
    return (
        _OperationalHandler(maybe_handle_auto_advance_command),
        _OperationalHandler(maybe_handle_bottleneck_command),
        _OperationalHandler(maybe_handle_patch_proposal_command),
        _OperationalHandler(maybe_handle_action_candidate_command),
        _OperationalHandler(maybe_handle_execution_package_command),
        _OperationalHandler(maybe_handle_implementation_handoff_command),
        _OperationalHandler(maybe_handle_handoff_application_command),
        _OperationalHandler(maybe_handle_handoff_validation_command),
        _OperationalHandler(maybe_handle_handoff_retry_command),
        _OperationalHandler(maybe_handle_codex_implementation_request_command),
        _OperationalHandler(maybe_handle_codex_outbox_command),
        _OperationalHandler(maybe_handle_codex_inbox_command),
        _OperationalHandler(maybe_handle_codex_channel_command),
        _OperationalHandler(maybe_handle_approval_gate_command),
        _OperationalHandler(maybe_handle_verification_command),
        _OperationalHandler(maybe_handle_self_evolution_command),
        _OperationalHandler(maybe_handle_directives_command, refresh_improvement_brain=False, announce_codex_suggestion=False),
        _OperationalHandler(maybe_handle_long_memory_command, refresh_improvement_brain=False, announce_codex_suggestion=False),
        _OperationalHandler(maybe_handle_operational_context_command),
    )


def maybe_handle_operational_command(user_input: str) -> OperationalCommandResult | None:
    for handler in _operational_handlers():
        response = handler.handle(user_input)
        if response:
            return OperationalCommandResult(
                response=response,
                refresh_improvement_brain=handler.refresh_improvement_brain,
                announce_codex_suggestion=handler.announce_codex_suggestion,
            )
    return None
