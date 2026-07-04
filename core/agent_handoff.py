from __future__ import annotations

from core.agent_operations import format_agent_operations_detail
from core.agent_tool_library import tool_library_for_chain
from core.decision_orchestrator import build_decision_plan
from core.response_polish import polish_assistant_response
from core.router_registry import INTENT_LEVEL_QUESTION


def _action_names_for_agent(agent: str, libraries: tuple[dict, ...] | list[dict]) -> str:
    for library in libraries:
        if str(library.get("agent") or "") != agent:
            continue
        actions = library.get("actions") or []
        names = [str(item.get("name") or "").strip() for item in actions[:5] if str(item.get("name") or "").strip()]
        return ", ".join(names) if names else "sem action direta listada"
    return "sem biblioteca carregada"


def format_handoff_plan_for_task(task: str, *, intent: str = "respond", complexity_kind: str = "complex_reasoning") -> str:
    raw_task = str(task or "").strip()
    if not raw_task:
        return "Diga a tarefa para eu montar o handoff entre agentes."

    plan = build_decision_plan(
        raw_task,
        {"intent": intent or "respond"},
        intent_level=INTENT_LEVEL_QUESTION,
        complexity_kind=complexity_kind or "complex_reasoning",
    )
    chain = list(plan.handoff_chain or [])
    if not chain:
        return "Não consegui montar uma cadeia de handoff para essa tarefa."

    libraries = plan.tool_libraries or tuple(tool_library_for_chain(chain, include_write=True, limit_per_agent=8))
    rows = []
    for index, item in enumerate(chain, start=1):
        agent = str(item.get("agent") or "--")
        role = "principal" if item.get("role") == "primary" else "apoio"
        actions = _action_names_for_agent(agent, libraries)
        rows.append(
            f"{index}. {agent} como {role}, toolset {item.get('toolset', '--')}, "
            f"motivo: {item.get('reason', 'domínio detectado')}. Actions iniciais: {actions}"
        )

    coordination = "handoff multiagente" if plan.coordination_mode == "multi_agent_handoff" else "agente único com contexto de apoio"
    return polish_assistant_response(
        f"Handoff para a tarefa: {raw_task}. Coordenação: {coordination}. "
        f"Agente principal: {plan.agent}. Política de modelo: {plan.model_policy}. "
        "Cadeia: " + " | ".join(rows) + "."
    )


def format_agent_handoff_detail(agent_name: str) -> str:
    return format_agent_operations_detail(agent_name)
