from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from actions import ensure_default_actions, list_actions


@dataclass(frozen=True)
class AgentToolProfile:
    agent: str
    categories: tuple[str, ...]
    notes: tuple[str, ...] = ()


AGENT_TOOL_PROFILES = {
    "dev_agent": AgentToolProfile(
        agent="dev_agent",
        categories=("code", "files", "actions", "memory"),
        notes=("ler e inspecionar codigo", "alterar arquivos so com governanca"),
    ),
    "research_agent": AgentToolProfile(
        agent="research_agent",
        categories=("web", "browser", "actions", "memory"),
        notes=("buscar fontes", "separar fato de leitura"),
    ),
    "investment_agent": AgentToolProfile(
        agent="investment_agent",
        categories=("investments", "web", "browser", "memory", "actions"),
        notes=("usar snapshot local antes de buscar dado externo",),
    ),
    "browser_agent": AgentToolProfile(
        agent="browser_agent",
        categories=("browser", "web", "vision", "ui", "actions"),
        notes=("ler pagina antes de agir", "confirmar acao externa sensivel"),
    ),
    "system_agent": AgentToolProfile(
        agent="system_agent",
        categories=("system", "media", "automation", "actions"),
        notes=("preferir comandos locais", "confirmar risco alto"),
    ),
    "memory_agent": AgentToolProfile(
        agent="memory_agent",
        categories=("memory", "actions", "files"),
        notes=("deduplicar fatos", "preservar privacidade"),
    ),
    "voice_agent": AgentToolProfile(
        agent="voice_agent",
        categories=("conversation", "system", "media", "actions"),
        notes=("responder curto", "lidar com comandos ambiguos"),
    ),
}


def categories_for_agent(agent: str) -> tuple[str, ...]:
    profile = AGENT_TOOL_PROFILES.get(str(agent or "").strip())
    return profile.categories if profile else ("actions",)


def tool_library_for_agent(agent: str, *, include_write: bool = True, limit: int = 40) -> dict[str, Any]:
    ensure_default_actions()
    categories = set(categories_for_agent(agent))
    actions = [
        action
        for action in list_actions()
        if action.category in categories and (include_write or action.read_only)
    ]
    actions = sorted(actions, key=lambda action: (action.category, action.name))[: max(1, int(limit))]
    return {
        "agent": str(agent or "").strip() or "unknown",
        "categories": sorted(categories),
        "actions": [
            {
                "name": action.name,
                "category": action.category,
                "description": action.description,
                "read_only": action.read_only,
                "requires_confirmation": action.requires_confirmation,
            }
            for action in actions
        ],
        "notes": list((AGENT_TOOL_PROFILES.get(str(agent or "").strip()) or AgentToolProfile(agent="unknown", categories=("actions",))).notes),
    }


def tool_library_for_chain(chain: list[dict] | tuple[dict, ...], *, include_write: bool = True, limit_per_agent: int = 20) -> list[dict]:
    libraries = []
    seen = set()
    for item in chain or []:
        if not isinstance(item, dict):
            continue
        agent = str(item.get("agent") or "").strip()
        if not agent or agent in seen:
            continue
        seen.add(agent)
        libraries.append(tool_library_for_agent(agent, include_write=include_write, limit=limit_per_agent))
    return libraries


def format_agent_tool_library(agent: str, *, limit: int = 12) -> str:
    library = tool_library_for_agent(agent, limit=limit)
    actions = library.get("actions") or []
    if not actions:
        return f"Biblioteca de ferramentas de {library['agent']}: sem actions disponiveis."
    rows = [
        f"{item['name']} [{item['category']}, {'leitura' if item['read_only'] else 'escrita'}]"
        for item in actions[:limit]
    ]
    categories = ", ".join(str(item) for item in library.get("categories") or [])
    notes = "; ".join(str(item) for item in library.get("notes") or [])
    notes_text = f" Notas: {notes}." if notes else ""
    return f"Biblioteca de ferramentas de {library['agent']}: categorias {categories}. Actions: " + "; ".join(rows) + "." + notes_text
