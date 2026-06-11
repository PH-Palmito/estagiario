from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.permission_policy import command_requires_confirmation
from core.sandbox_policy import command_sandbox_decision

RouteStep = Callable[[str], dict]
PlanActions = Callable[[str], list | None]
SplitLocalSteps = Callable[[str], list[str]]
ProcessAction = Callable[[dict], object | str]
ExecuteCommand = Callable[[object], str]

REPEATED_NOISE = {
    "Nao sei o que fechar.",
    "Pode repetir?",
    "Nao entendi.",
}


@dataclass(frozen=True)
class RoutineDryRunStep:
    command: object | None
    message: str
    executable: bool


def append_multi_step_result(results: list[str], result: str) -> None:
    if result in REPEATED_NOISE and result in results:
        return
    results.append(result)


def _attach_step_input(raw_action, step: str):
    if not isinstance(raw_action, dict):
        return raw_action
    payload = dict(raw_action)
    payload.setdefault("__user_input", step)
    return payload


def routine_dry_run_block_message(command, *, prefix: str) -> str | None:
    if command_requires_confirmation(command):
        return f"{prefix}: {command.action} {getattr(command, 'params', {})}"

    sandbox = command_sandbox_decision(command)
    if sandbox.requires_confirmation or sandbox.dry_run_recommended:
        return f"{prefix}: {command.action} {getattr(command, 'params', {})}"

    return None


def dry_run_routine_plan(
    steps,
    *,
    route_step: RouteStep,
    process_action: ProcessAction,
    invalid_message: str,
    sensitive_prefix: str,
) -> list[RoutineDryRunStep] | str:
    if not isinstance(steps, list):
        return "Rotina invalida."

    dry_run: list[RoutineDryRunStep] = []
    for step in steps:
        if isinstance(step, str):
            if not step.strip():
                dry_run.append(RoutineDryRunStep(None, invalid_message, False))
                continue
            raw_action = _attach_step_input(route_step(step), step)
        elif isinstance(step, dict):
            raw_action = step
        else:
            dry_run.append(RoutineDryRunStep(None, invalid_message, False))
            continue

        processed = process_action(raw_action)
        if isinstance(processed, str):
            dry_run.append(RoutineDryRunStep(None, processed, False))
            continue

        block_message = routine_dry_run_block_message(processed, prefix=sensitive_prefix)
        if block_message:
            dry_run.append(RoutineDryRunStep(processed, block_message, False))
            continue

        dry_run.append(RoutineDryRunStep(processed, "", True))

    return dry_run


def handle_multi_step_request(
    user_input: str,
    *,
    split_local_steps: SplitLocalSteps,
    plan_actions: PlanActions,
    route_step: RouteStep,
    process_action: ProcessAction,
    execute_command: ExecuteCommand,
) -> str | None:
    local_steps = split_local_steps(user_input)
    plan = None

    if len(local_steps) > 1:
        plan = [_attach_step_input(route_step(step), step) for step in local_steps]
    elif "," in user_input:
        return None
    else:
        plan = plan_actions(user_input)

    if not plan or not isinstance(plan, list):
        return None

    dry_run = dry_run_routine_plan(
        plan,
        route_step=route_step,
        process_action=process_action,
        invalid_message="Etapa invalida no plano.",
        sensitive_prefix="Acao sensivel no plano bloqueada",
    )
    if isinstance(dry_run, str):
        return dry_run

    results: list[str] = []
    for item in dry_run:
        if not item.executable:
            append_multi_step_result(results, item.message)
            continue

        append_multi_step_result(results, execute_command(item.command))

    return "\n".join(results)


def execute_routine_steps(
    steps,
    *,
    route_step: RouteStep,
    process_action: ProcessAction,
    execute_command: ExecuteCommand,
) -> str:
    dry_run = dry_run_routine_plan(
        steps,
        route_step=route_step,
        process_action=process_action,
        invalid_message="Etapa invalida na rotina.",
        sensitive_prefix="Etapa sensivel bloqueada",
    )
    if isinstance(dry_run, str):
        return dry_run

    results: list[str] = []
    for item in dry_run:
        if not item.executable:
            results.append(item.message)
            continue

        results.append(execute_command(item.command))

    return "\n".join(results)
