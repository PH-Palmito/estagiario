from __future__ import annotations

from core.router_utils import normalize_text
from memory.self_evolution import load_self_evolution_plan, save_self_evolution_plan


def _summarize_plan_counts(plan: dict) -> tuple[int, int, int, int, list[dict]]:
    steps = plan.get("steps") or []
    steps = steps if isinstance(steps, list) else []
    done = sum(1 for step in steps if isinstance(step, dict) and step.get("status") == "done")
    next_items = [step for step in steps if isinstance(step, dict) and step.get("status") == "next"]
    planned = sum(1 for step in steps if isinstance(step, dict) and step.get("status") == "planned")
    left = max(0, len(steps) - done)
    return len(steps), done, left, planned, next_items


def maybe_handle_self_evolution_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "plano de auto evolucao",
        "mostrar plano de auto evolucao",
        "auto evolucao",
        "como chegar em se reescreve sozinho",
    }:
        plan = load_self_evolution_plan()
        steps = plan.get("steps") or []
        if not isinstance(steps, list) or not steps:
            return "Ainda nao consegui montar um plano de auto evolucao."
        lines = []
        for step in steps[:4]:
            if not isinstance(step, dict):
                continue
            status = str(step.get("status", "planned")).strip()
            title = str(step.get("title", "")).strip()
            if title:
                lines.append(f"{status}: {title}")
        focus = str(plan.get("current_focus", "")).strip()
        prefix = f"Foco atual: {focus}. " if focus else ""
        return prefix + "Plano de auto evolucao do Axel: " + "; ".join(lines)

    if normalized in {
        "quantos passos faltam",
        "quantos passos faltam para auto evolucao",
        "status da auto evolucao",
        "progresso da auto evolucao",
        "andamento da auto evolucao",
    }:
        plan = save_self_evolution_plan()
        total, done, left, planned, next_items = _summarize_plan_counts(plan)
        next_title = str((next_items[0] if next_items else {}).get("title", "")).strip()
        suffix = f" Proximo passo: {next_title}." if next_title else ""
        return f"Auto evolucao do Axel: {done}/{total} passos concluidos. Faltam {left}; {planned} ainda planejados.{suffix}"

    if normalized in {
        "listar passos faltantes",
        "mostrar passos faltantes",
        "quais passos faltam",
        "passos restantes",
        "passos que faltam",
    }:
        plan = save_self_evolution_plan()
        missing = [
            step
            for step in plan.get("steps", [])
            if isinstance(step, dict) and step.get("status") != "done"
        ]
        if not missing:
            return "Todos os passos conhecidos da auto evolucao estao concluidos."
        parts = []
        for index, step in enumerate(missing[:8], start=1):
            status = str(step.get("status", "planned")).strip()
            title = str(step.get("title", "")).strip()
            if title:
                parts.append(f"{index}. {status}: {title}")
        return "Passos faltantes: " + "; ".join(parts)

    if normalized in {
        "proximo passo da auto evolucao",
        "qual o proximo passo",
        "qual o proximo passo da auto evolucao",
        "avancar auto evolucao",
    }:
        plan = save_self_evolution_plan()
        _, _, _, _, next_items = _summarize_plan_counts(plan)
        if next_items:
            step = next_items[0]
        else:
            planned_items = [item for item in plan.get("steps", []) if isinstance(item, dict) and item.get("status") == "planned"]
            step = planned_items[0] if planned_items else {}
        title = str(step.get("title", "")).strip()
        reason = str(step.get("reason", "")).strip()
        if title and reason:
            return f"Proximo passo da auto evolucao: {title}. Motivo: {reason}"
        if title:
            return f"Proximo passo da auto evolucao: {title}."
        return "Todos os passos conhecidos da auto evolucao estao concluidos ou sem proximo item definido."

    if normalized in {
        "atualizar plano de auto evolucao",
        "gerar plano de auto evolucao",
    }:
        plan = save_self_evolution_plan()
        focus = str(plan.get("current_focus", "")).strip()
        if focus:
            return f"Atualizei o plano de auto evolucao. Foco atual: {focus}."
        return "Atualizei o plano de auto evolucao do Axel."

    return None
