from __future__ import annotations

from core.agent_tool_library import tool_library_for_agent
from core.response_polish import polish_assistant_response
from core.specialist_agents import find_agent, list_agents
from memory.capability_ranking import capability_rankings


def _agent_stats(agent_name: str) -> dict:
    rows = capability_rankings(limit=50).get("agent") or []
    for row in rows:
        if str(row.get("name") or "") == agent_name:
            return row
    return {
        "name": agent_name,
        "total": 0,
        "success": 0,
        "failure": 0,
        "needs_adjustment": 0,
        "success_rate": 0.0,
        "error_rate": 0.0,
        "utility": 0.0,
        "recent_actions": [],
    }


def _format_agent_row(agent: dict) -> str:
    stats = _agent_stats(str(agent.get("name") or ""))
    usage = int(stats.get("total") or 0)
    success = int(stats.get("success") or 0)
    failures = int(stats.get("failure") or 0)
    adjustments = int(stats.get("needs_adjustment") or 0)
    return (
        f"{agent.get('title')} ({agent.get('name')}): toolset {agent.get('toolset')}, "
        f"uso {usage}, sucesso {success}, falhas {failures}, ajustes {adjustments}"
    )


def format_agent_operations_overview() -> str:
    agents = list_agents()
    rows = [_format_agent_row(agent) for agent in agents]
    return polish_assistant_response(
        "Agentes operacionais do Axel: "
        + " | ".join(rows)
        + ". Use `detalhar agente dev_agent` ou `ferramentas do agente dev_agent` para ver responsabilidades e actions."
    )


def format_agent_operations_detail(name_or_title: str) -> str:
    agent = find_agent(name_or_title)
    if not agent:
        return "Não encontrei esse agente. Use `agentes operacionais do Axel` para ver os nomes."

    library = tool_library_for_agent(str(agent.get("name") or ""), limit=8)
    actions = library.get("actions") or []
    action_rows = [
        f"{item.get('name')} ({'leitura' if item.get('read_only') else 'escrita'})"
        for item in actions[:8]
    ]
    stats = _agent_stats(str(agent.get("name") or ""))
    recent_actions = ", ".join(str(item) for item in (stats.get("recent_actions") or [])[:5]) or "sem histórico recente"
    triggers = ", ".join(str(item) for item in (agent.get("triggers") or [])[:8])
    rules = ", ".join(str(item) for item in (agent.get("handoff_rules") or [])[:4])
    categories = ", ".join(str(item) for item in library.get("categories") or [])
    action_text = "; ".join(action_rows) if action_rows else "sem actions disponíveis"

    return polish_assistant_response(
        f"{agent.get('title')} ({agent.get('name')}): {agent.get('mission')} "
        f"Toolset: {agent.get('toolset')}. Política de modelo: {agent.get('model_policy')}. "
        f"Gatilhos: {triggers}. Regras: {rules}. Categorias: {categories}. "
        f"Actions úteis: {action_text}. Métricas: uso {int(stats.get('total') or 0)}, "
        f"sucesso {int(stats.get('success') or 0)}, falhas {int(stats.get('failure') or 0)}, "
        f"ajustes {int(stats.get('needs_adjustment') or 0)}, utilidade {stats.get('utility') or 0}. "
        f"Ações recentes: {recent_actions}."
    )


def format_agent_operations_for_query(query: str) -> str:
    agent = find_agent(query)
    if agent:
        return format_agent_operations_detail(str(agent.get("name") or query))
    return "Não encontrei um agente específico para isso. " + format_agent_operations_overview()
