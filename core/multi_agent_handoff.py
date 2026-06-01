from __future__ import annotations

from core.specialist_agents import agent_for_toolset, select_agents
from core.toolsets import select_toolsets


def build_handoff_chain(user_input: str, intent: str, *, primary_toolset: str, primary_agent: str, limit: int = 4) -> list[dict]:
    query = f"{user_input} {intent}"
    selected_toolsets = select_toolsets(query, limit=limit)
    chain = []
    seen_agents = set()

    for toolset in selected_toolsets:
        toolset_name = str(toolset.get("name") or "").strip()
        if not toolset_name:
            continue
        agent_matches = [
            item for item in select_agents(query, toolset=toolset_name, limit=4)
            if str(item.get("toolset") or "").strip() == toolset_name
        ]
        agent = agent_matches[0] if agent_matches else agent_for_toolset(toolset_name)
        agent_name = str(agent.get("name") or "").strip()
        if not agent_name or agent_name in seen_agents:
            continue
        seen_agents.add(agent_name)
        chain.append(
            {
                "agent": agent_name,
                "toolset": toolset_name,
                "role": "primary" if agent_name == primary_agent or toolset_name == primary_toolset else "handoff",
                "mission": str(agent.get("mission") or "").strip(),
                "reason": "dominio principal" if agent_name == primary_agent or toolset_name == primary_toolset else "dominio complementar detectado",
            }
        )

    if not any(item.get("agent") == primary_agent for item in chain):
        chain.insert(
            0,
            {
                "agent": primary_agent,
                "toolset": primary_toolset,
                "role": "primary",
                "mission": "",
                "reason": "agente principal do plano",
            },
        )

    if len(chain) == 1:
        return chain
    return chain[: max(1, int(limit))]


def handoff_needed(user_input: str, intent: str, *, intent_level: str, complexity_kind: str, chain: list[dict]) -> bool:
    if len(chain) < 2:
        return False
    normalized = f"{user_input} {intent} {intent_level} {complexity_kind}".lower()
    explicit = any(token in normalized for token in (" e ", " depois ", "com fontes", "comparar", "resumir", "codigo", "site", "carteira", "investimento"))
    complex_level = intent_level in {"tarefa_composta", "composite_task"} or complexity_kind in {"multi_step", "complex_reasoning"}
    return bool(explicit or complex_level)


def format_handoff_chain(chain: list[dict]) -> str:
    if not chain:
        return "sem handoff registrado"
    rows = []
    for item in chain:
        rows.append(f"{item.get('agent', '--')} via {item.get('toolset', '--')} ({item.get('role', 'handoff')})")
    return " -> ".join(rows)
