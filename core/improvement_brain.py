from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from memory.action_candidates import save_action_candidates
from memory.approval_gate import sync_approval_gate
from memory.auto_advances import save_auto_advances
from memory.bottlenecks import save_bottlenecks
from memory.codex_bridge import save_codex_request
from memory.codex_channel import save_codex_channel
from memory.codex_implementation_request import save_codex_implementation_request
from memory.codex_notifications import consume_codex_suggestion
from memory.codex_outbox import sync_codex_outbox
from memory.execution_packages import save_execution_package
from memory.handoff_applications import sync_handoff_application
from memory.handoff_retry_plan import save_handoff_retry_plan
from memory.handoff_validation import save_handoff_validation
from memory.implementation_handoff import save_implementation_handoff
from memory.operational_context import save_operational_context
from memory.patch_proposals import save_patch_proposals
from memory.self_evolution import save_self_evolution_plan
from memory.verification_runs import sync_verification_runs


def default_improvement_steps() -> list[Callable[[], object]]:
    return [
        save_bottlenecks,
        save_auto_advances,
        save_patch_proposals,
        save_action_candidates,
        save_execution_package,
        save_implementation_handoff,
        sync_handoff_application,
        save_handoff_validation,
        save_handoff_retry_plan,
        save_codex_implementation_request,
        sync_approval_gate,
        sync_verification_runs,
        save_codex_request,
        save_codex_channel,
        sync_codex_outbox,
        save_operational_context,
        save_self_evolution_plan,
    ]


@dataclass
class ImprovementBrain:
    steps: list[Callable[[], object]] = field(default_factory=default_improvement_steps)
    consume_codex_suggestion: Callable[[], str] = consume_codex_suggestion
    output_response: Callable[..., None] | None = None
    now_fn: Callable[[], float] = time.time
    min_interval_seconds: float = 15.0
    last_refresh_at: float = 0.0

    def refresh(self, force: bool = False) -> bool:
        now = self.now_fn()
        if not force and now - self.last_refresh_at < self.min_interval_seconds:
            return False

        try:
            for step in self.steps:
                step()
            self.last_refresh_at = now
            return True
        except Exception:
            return False

    def maybe_announce_codex_suggestion(self, voice_mode: bool) -> bool:
        suggestion = self.consume_codex_suggestion()
        if not suggestion or self.output_response is None:
            return False

        self.output_response(suggestion, voice_mode)
        return True
