from __future__ import annotations

import time
from collections.abc import Callable

from core.action_result import normalize_action_result
from core.axel_brain_effects import apply_plan_to_command
from core.action_governance import command_audit_required, command_governance_payload
from core.command_schema import Command
from core.context_resolver import resolve_params
from core.intent_judge import judge_command_interpretation
from core.intent_llm_judge import llm_review_to_judge_result, review_intent_with_llm, should_request_llm_intent_review
from core.latency_metrics import log_latency_stage
from core.normalizer import normalize_action
from core.permission_policy import permission_decision
from core.performance_policy import default_action_performance_advice
from core.response_provenance import record_tool_use
from memory.sensitive_audit import append_sensitive_action_audit
from memory.task_evaluation import record_task_evaluation
from core.validator import validate_command

LogEvent = Callable[..., None]


def _runtime_evaluation_metadata(runtime_state) -> dict:
    metadata = {}
    plan = getattr(runtime_state, "axel_brain_plan", {}) or {}
    if isinstance(plan, dict):
        for key in ("intent", "agent", "toolset", "model_policy", "risk_level", "response_mode", "coordination_mode"):
            value = str(plan.get(key) or "").strip()
            if value:
                metadata[key] = value
        chain = plan.get("handoff_chain")
        if isinstance(chain, (list, tuple)):
            metadata["handoff_agents"] = [
                str(item.get("agent") or "").strip()
                for item in chain
                if isinstance(item, dict) and str(item.get("agent") or "").strip()
            ][:4]
        libraries = plan.get("tool_libraries")
        if isinstance(libraries, (list, tuple)):
            metadata["tool_library_agents"] = [
                str(item.get("agent") or "").strip()
                for item in libraries
                if isinstance(item, dict) and str(item.get("agent") or "").strip()
            ][:4]

    trace = getattr(runtime_state, "last_route_trace", {}) or {}
    if isinstance(trace, dict):
        for key in ("group", "detector", "intent_level", "complexity"):
            value = str(trace.get(key) or "").strip()
            if value:
                metadata[f"route_{key}"] = value
        user_input = str(trace.get("input") or "").strip()
        if user_input:
            metadata["user_input"] = user_input[:240]
            try:
                from memory.procedural_skills import search_skills

                skills = [
                    str(item.get("name") or "").strip()
                    for item in search_skills(user_input, limit=3)
                    if str(item.get("name") or "").strip()
                ]
                if skills:
                    metadata["skills"] = skills
            except Exception:
                pass
    return metadata


def command_permission_payload(command: Command) -> dict:
    decision = permission_decision(command)
    return {
        "tool_name": decision.tool_name,
        "category": decision.category,
        "read_only": decision.read_only,
        "requires_confirmation": decision.requires_confirmation,
        "requires_strong_confirmation": decision.requires_strong_confirmation,
        "risk_level": decision.risk_level,
        "sandbox_scope": decision.sandbox_scope,
        "dry_run_recommended": decision.dry_run_recommended,
        **command_governance_payload(command),
    }


def should_audit_command(command: Command) -> bool:
    return command_audit_required(permission_decision(command))


def audit_sensitive_command(event_type: str, command: Command, **payload) -> None:
    if not should_audit_command(command):
        return
    try:
        append_sensitive_action_audit(
            event_type,
            {
                "action": getattr(command, "action", ""),
                "params": getattr(command, "params", {}),
                **command_permission_payload(command),
                **payload,
            },
        )
    except Exception:
        pass


def should_auto_background(command: Command) -> bool:
    action = str(getattr(command, "action", "") or "").strip()
    if not action or action.startswith("background"):
        return False
    if action == "action_tool_execute":
        return False

    advice = default_action_performance_advice(action)
    if not advice.should_background:
        return False

    decision = permission_decision(command)
    if not decision.read_only or decision.requires_confirmation or decision.requires_strong_confirmation:
        return False
    return True


def _submit_command_background_task(
    command: Command,
    execute: Callable[[Command], object],
    log_event: LogEvent,
) -> str:
    from core.background_tasks import submit_background_task

    def run() -> str:
        action_result = normalize_action_result(execute(command))
        if not action_result.success:
            raise RuntimeError(action_result.error or action_result.message)
        return action_result.message

    task_id = submit_background_task(
        command.action,
        run,
    )
    log_event(
        "command_auto_background",
        action=getattr(command, "action", ""),
        params=getattr(command, "params", {}),
        task_id=task_id,
        **command_permission_payload(command),
    )
    return f"Deixei {command.action} rodando em segundo plano. Tarefa: {task_id}."


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
        **command_permission_payload(command),
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

    route_trace = getattr(runtime_state, "last_route_trace", {}) or {}
    user_input = str(raw_action.get("__user_input") or route_trace.get("input") or "")
    judge = judge_command_interpretation(user_input, command, route_trace=route_trace)
    if judge.allowed and should_request_llm_intent_review(
        user_input,
        command,
        route_trace=route_trace,
        decision_plan=getattr(runtime_state, "axel_brain_plan", {}) or {},
    ):
        review = review_intent_with_llm(
            user_input,
            command,
            route_trace=route_trace,
            decision_plan=getattr(runtime_state, "axel_brain_plan", {}) or {},
        )
        llm_judge = llm_review_to_judge_result(review)
        log_event(
            "intent_llm_judge",
            action=getattr(command, "action", ""),
            params=getattr(command, "params", {}),
            verdict=getattr(review, "verdict", "") if review else "",
            allowed=llm_judge.allowed,
            requires_confirmation=llm_judge.requires_confirmation,
            reason=llm_judge.reason,
        )
        if not llm_judge.allowed or llm_judge.requires_confirmation:
            judge = llm_judge
    log_event(
        "intent_judge",
        action=getattr(command, "action", ""),
        params=getattr(command, "params", {}),
        allowed=judge.allowed,
        requires_confirmation=judge.requires_confirmation,
        reason=judge.reason,
    )
    if not judge.allowed:
        return judge.message or "Segurei essa ação por falta de clareza. Reformule o pedido ou confirme com mais detalhes."
    if judge.requires_confirmation:
        command.requires_confirmation = True

    brain_effects = apply_plan_to_command(command, getattr(runtime_state, "axel_brain_plan", {}) or {})
    log_event(
        "axel_brain_command_effects",
        action=getattr(command, "action", ""),
        **brain_effects,
    )

    return command


def execute_processed_command(
    command: Command,
    runtime_state,
    execute: Callable[[Command], object],
    log_event: LogEvent,
    progress_callback: Callable[[Command], None] | None = None,
    voice_mode: bool = False,
) -> str:
    if progress_callback is not None:
        progress_callback(command)

    started_at = time.time()
    performance_advice = default_action_performance_advice(getattr(command, "action", ""))
    if performance_advice.mode != "foreground_ok":
        log_event(
            "command_performance_advice",
            action=performance_advice.action,
            mode=performance_advice.mode,
            reason=performance_advice.reason,
            should_background=performance_advice.should_background,
            should_cache=performance_advice.should_cache,
        )
    if should_auto_background(command):
        record_tool_use(getattr(command, "action", ""), getattr(command, "params", {}))
        result = _submit_command_background_task(command, execute, log_event)
        runtime_state.update(command, result)
        return result

    log_event(
        "command_execute_start",
        action=getattr(command, "action", ""),
        params=getattr(command, "params", {}),
        voice_mode=voice_mode,
        **command_permission_payload(command),
    )
    audit_sensitive_command("command_execute_start", command, voice_mode=voice_mode)
    action_started_at = time.perf_counter()
    try:
        raw_result = execute(command)
        action_result = normalize_action_result(raw_result)
        result = action_result.message
        record_tool_use(getattr(command, "action", ""), getattr(command, "params", {}))
        runtime_state.update(command, result)
        log_event(
            "command_execute_end",
            action=getattr(command, "action", ""),
            params=getattr(command, "params", {}),
            result=result,
            success=action_result.success,
            error=action_result.error,
            voice_mode=voice_mode,
            duration_ms=round((time.time() - started_at) * 1000, 2),
            **command_permission_payload(command),
        )
        try:
            record_task_evaluation(
                action=getattr(command, "action", ""),
                success=action_result.success,
                source="auto",
                result=result,
                error=action_result.error,
                metadata={
                    "voice_mode": voice_mode,
                    **_runtime_evaluation_metadata(runtime_state),
                    **command_permission_payload(command),
                },
            )
        except Exception:
            pass
        audit_sensitive_command(
            "command_execute_end",
            command,
            result=result,
            success=action_result.success,
            error=action_result.error,
            voice_mode=voice_mode,
            duration_ms=round((time.time() - started_at) * 1000, 2),
        )
        return result
    finally:
        log_latency_stage(
            log_event,
            "action",
            action_started_at,
            action=getattr(command, "action", ""),
            voice_mode=voice_mode,
        )
