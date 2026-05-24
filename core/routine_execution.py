from __future__ import annotations

from collections.abc import Callable

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


def append_multi_step_result(results: list[str], result: str) -> None:
    if result in REPEATED_NOISE and result in results:
        return
    results.append(result)


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
        plan = [route_step(step) for step in local_steps]
    elif "," in user_input:
        return None
    else:
        plan = plan_actions(user_input)

    if not plan or not isinstance(plan, list):
        return None

    results: list[str] = []
    for step in plan:
        processed = process_action(step)

        if isinstance(processed, str):
            append_multi_step_result(results, processed)
            continue

        if getattr(processed, "requires_confirmation", False):
            append_multi_step_result(
                results,
                f"Acao sensivel no plano bloqueada: {processed.action} {processed.params}",
            )
            continue

        append_multi_step_result(results, execute_command(processed))

    return "\n".join(results)


def execute_routine_steps(
    steps,
    *,
    route_step: RouteStep,
    process_action: ProcessAction,
    execute_command: ExecuteCommand,
) -> str:
    if not isinstance(steps, list):
        return "Rotina invalida."

    results: list[str] = []
    for step in steps:
        if not isinstance(step, str) or not step.strip():
            results.append("Etapa invalida na rotina.")
            continue

        raw_action = route_step(step)
        processed = process_action(raw_action)

        if isinstance(processed, str):
            results.append(processed)
            continue

        if getattr(processed, "requires_confirmation", False):
            results.append(f"Etapa sensivel bloqueada: {processed.action}")
            continue

        results.append(execute_command(processed))

    return "\n".join(results)
