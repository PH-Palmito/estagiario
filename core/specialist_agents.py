from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SpecialistAgent:
    name: str
    title: str
    toolset: str
    model_policy: str
    mission: str
    handoff_rules: tuple[str, ...]
    triggers: tuple[str, ...]


AGENTS = (
    SpecialistAgent(
        name="dev_agent",
        title="Agente de Programacao",
        toolset="programacao",
        model_policy="nvidia_or_gemini_for_reasoning",
        mission="Entender, modificar, revisar e testar codigo com seguranca.",
        handoff_rules=("ler contexto antes de editar", "preservar mudancas do usuario", "rodar testes focados"),
        triggers=("codigo", "bug", "teste", "refatorar", "implementar", "python", "projeto"),
    ),
    SpecialistAgent(
        name="research_agent",
        title="Agente de Pesquisa",
        toolset="pesquisa",
        model_policy="cloud_with_sources",
        mission="Buscar, comparar e sintetizar informacoes atuais com separacao entre fato e leitura.",
        handoff_rules=("verificar fonte quando o dado for atual", "citar limite da informacao", "evitar certeza falsa"),
        triggers=("pesquisar", "noticia", "fonte", "comparar", "atual", "mercado", "governo"),
    ),
    SpecialistAgent(
        name="study_agent",
        title="Agente de Estudos",
        toolset="estudos",
        model_policy="nvidia_or_gemini_for_reasoning",
        mission="Analisar materiais de estudo, resumir, gerar questões, corrigir respostas e manter contexto do arquivo atual.",
        handoff_rules=("validar extração antes de resumir", "separar resumo de gabarito", "registrar contexto de estudo útil"),
        triggers=("estudo", "estudar", "pdf", "slide", "slides", "arquivo", "questoes", "questões", "revisao", "revisão"),
    ),
    SpecialistAgent(
        name="investment_agent",
        title="Agente de Investimentos",
        toolset="carteira",
        model_policy="grounded_cloud_when_current",
        mission="Analisar carteira, dividendos, ativos, noticias e riscos sem recomendacao financeira direta.",
        handoff_rules=("usar snapshot local primeiro", "buscar dado atual quando necessario", "separar fato, leitura e limite"),
        triggers=("carteira", "investimento", "dividendo", "fii", "acao", "ativo", "preco teto"),
    ),
    SpecialistAgent(
        name="browser_agent",
        title="Agente de Navegacao",
        toolset="navegador",
        model_policy="local_for_commands_cloud_for_summary",
        mission="Ler, resumir, navegar e interagir com paginas de forma previsivel.",
        handoff_rules=("ler pagina antes de inferir", "confirmar acoes sensiveis", "preferir alvos visiveis"),
        triggers=("navegador", "site", "pagina", "clicar", "web", "resumir pagina"),
    ),
    SpecialistAgent(
        name="system_agent",
        title="Agente de Sistema",
        toolset="sistema",
        model_policy="local_first",
        mission="Executar automacoes locais de apps, janelas, teclado, mouse, audio e Windows.",
        handoff_rules=("confirmar risco alto", "preferir comandos locais", "manter feedback curto em voz"),
        triggers=("abrir app", "janela", "teclado", "mouse", "volume", "windows", "led"),
    ),
    SpecialistAgent(
        name="memory_agent",
        title="Agente de Memoria",
        toolset="memoria",
        model_policy="local_first",
        mission="Organizar memoria curta, sessoes antigas, preferencias, skills e contexto operacional.",
        handoff_rules=("nao salvar dado passageiro como permanente", "deduplicar fatos", "preservar privacidade"),
        triggers=("memoria", "lembrar", "sessoes", "perfil", "preferencia", "skill", "contexto"),
    ),
    SpecialistAgent(
        name="voice_agent",
        title="Agente de Voz",
        toolset="voz_rapida",
        model_policy="local_first",
        mission="Cuidar de escuta, transcricao, fala, perfis de voz e comandos ambiguos.",
        handoff_rules=("responder curto", "confirmar transcricao duvidosa", "aprender correcoes recorrentes"),
        triggers=("voz", "microfone", "transcricao", "hotword", "falar", "escuta", "perfil de voz"),
    ),
)


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^\w\s/-]", " ", str(text or "").lower())
    return {token for token in normalized.split() if len(token) >= 3}


def list_agents() -> list[dict]:
    return [
        {
            "name": agent.name,
            "title": agent.title,
            "toolset": agent.toolset,
            "model_policy": agent.model_policy,
            "mission": agent.mission,
            "handoff_rules": list(agent.handoff_rules),
            "triggers": list(agent.triggers),
        }
        for agent in AGENTS
    ]


def agent_for_toolset(toolset: str) -> dict:
    normalized = str(toolset or "").strip()
    for agent in AGENTS:
        if agent.toolset == normalized:
            return list_agents()[AGENTS.index(agent)]
    return list_agents()[0]


def select_agents(query: str, *, toolset: str = "", limit: int = 3) -> list[dict]:
    query_tokens = _tokens(query)
    matches = []
    for agent in AGENTS:
        toolset_bonus = 3 if toolset and agent.toolset == toolset else 0
        trigger_overlap = query_tokens & _tokens(" ".join(agent.triggers))
        mission_overlap = query_tokens & _tokens(agent.mission)
        if not trigger_overlap and not mission_overlap and not toolset_bonus:
            continue
        score = toolset_bonus + (len(trigger_overlap) * 3) + len(mission_overlap)
        item = {
            "name": agent.name,
            "title": agent.title,
            "toolset": agent.toolset,
            "model_policy": agent.model_policy,
            "mission": agent.mission,
            "handoff_rules": list(agent.handoff_rules),
            "score": score,
            "matched_terms": sorted(trigger_overlap | mission_overlap),
        }
        matches.append(item)

    matches.sort(key=lambda item: (int(item["score"]), item["title"]), reverse=True)
    return matches[: max(1, int(limit))]


def format_agent_catalog() -> str:
    rows = [f"{agent.title} ({agent.name})" for agent in AGENTS]
    return "Agentes especialistas do Axel: " + "; ".join(rows) + "."


def format_relevant_agents(query: str, *, toolset: str = "", limit: int = 2) -> str:
    matches = select_agents(query, toolset=toolset, limit=limit)
    if not matches:
        return "Nenhum agente especialista especifico selecionado."
    rows = []
    for item in matches:
        rules = ", ".join(str(rule) for rule in item.get("handoff_rules", [])[:2])
        rows.append(f"{item['title']} ({item['name']}): {item['mission']} Regras: {rules}.")
    return "Agentes especialistas relevantes: " + " | ".join(rows)


def find_agent(name_or_title: str) -> dict | None:
    normalized = str(name_or_title or "").strip().lower()
    if not normalized:
        return None
    compact = re.sub(r"[^a-z0-9]+", "", normalized)
    for agent in list_agents():
        candidates = {
            str(agent.get("name") or "").lower(),
            str(agent.get("title") or "").lower(),
            str(agent.get("toolset") or "").lower(),
        }
        compact_candidates = {re.sub(r"[^a-z0-9]+", "", value) for value in candidates}
        if normalized in candidates or compact in compact_candidates:
            return agent
        if normalized.replace("agente de ", "") in candidates:
            return agent
    matches = select_agents(name_or_title, limit=1)
    return matches[0] if matches else None
