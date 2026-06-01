from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Toolset:
    name: str
    title: str
    triggers: tuple[str, ...]
    capabilities: tuple[str, ...]
    risks: tuple[str, ...]
    default_model_policy: str


TOOLSETS = (
    Toolset(
        name="voz_rapida",
        title="Voz rapida",
        triggers=("voz", "microfone", "hotword", "escuta", "comando rapido", "falar"),
        capabilities=("comandos locais seguros", "confirmacao curta", "resposta falada objetiva"),
        risks=("transcricao ambigua", "latencia perceptivel"),
        default_model_policy="local_first",
    ),
    Toolset(
        name="programacao",
        title="Programacao",
        triggers=("codigo", "bug", "teste", "refatorar", "implementar", "projeto", "python"),
        capabilities=("ler arquivos", "analisar codigo", "rodar testes", "preparar handoff para Codex"),
        risks=("mudanca em arquivo errado", "reverter alteracao do usuario", "comando destrutivo"),
        default_model_policy="nvidia_or_gemini_for_reasoning",
    ),
    Toolset(
        name="carteira",
        title="Carteira",
        triggers=("carteira", "investimento", "dividendo", "fii", "acao", "ativo", "preco teto"),
        capabilities=("snapshot local", "noticias", "fundamentos", "alertas de carteira"),
        risks=("dado financeiro desatualizado", "recomendacao indevida"),
        default_model_policy="grounded_cloud_when_current",
    ),
    Toolset(
        name="navegador",
        title="Navegador",
        triggers=("navegador", "site", "pagina", "clicar", "ler tela", "resumir pagina", "web"),
        capabilities=("abrir URL", "ler pagina", "clicar por texto", "resumir conteudo"),
        risks=("acao externa em site", "pagina dinamica", "login sensivel"),
        default_model_policy="local_for_commands_cloud_for_summary",
    ),
    Toolset(
        name="sistema",
        title="Sistema",
        triggers=("abrir app", "janela", "teclado", "mouse", "volume", "windows", "led"),
        capabilities=("apps", "janelas", "teclado", "mouse", "audio", "diagnostico local"),
        risks=("acao destrutiva", "perda de foco de janela", "efeito fora do Axel"),
        default_model_policy="local_first",
    ),
    Toolset(
        name="pesquisa",
        title="Pesquisa",
        triggers=("pesquisar", "noticia", "fonte", "comparar", "atual", "mercado", "governo"),
        capabilities=("buscar fontes", "comparar informacoes", "sintetizar resposta fundamentada"),
        risks=("informacao recente instavel", "fonte fraca", "misturar opiniao e fato"),
        default_model_policy="cloud_with_sources",
    ),
)


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^\w\s/-]", " ", str(text or "").lower())
    return {token for token in normalized.split() if len(token) >= 3}


def list_toolsets() -> list[dict]:
    return [
        {
            "name": item.name,
            "title": item.title,
            "triggers": list(item.triggers),
            "capabilities": list(item.capabilities),
            "risks": list(item.risks),
            "default_model_policy": item.default_model_policy,
        }
        for item in TOOLSETS
    ]


def select_toolsets(query: str, limit: int = 3) -> list[dict]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return []

    matches = []
    for item in TOOLSETS:
        trigger_text = " ".join(item.triggers)
        capability_text = " ".join(item.capabilities)
        trigger_overlap = query_tokens & _tokens(trigger_text)
        capability_overlap = query_tokens & _tokens(capability_text)
        if not trigger_overlap and not capability_overlap:
            continue
        score = (len(trigger_overlap) * 3) + len(capability_overlap)
        matches.append(
            {
                "name": item.name,
                "title": item.title,
                "capabilities": list(item.capabilities),
                "risks": list(item.risks),
                "default_model_policy": item.default_model_policy,
                "score": score,
                "matched_terms": sorted(trigger_overlap | capability_overlap),
            }
        )

    matches.sort(key=lambda item: (int(item["score"]), item["title"]), reverse=True)
    return matches[: max(1, int(limit))]


def format_toolset_catalog() -> str:
    rows = [f"{item.title} ({item.name})" for item in TOOLSETS]
    return "Toolsets do Axel: " + "; ".join(rows) + "."


def format_relevant_toolsets(query: str, limit: int = 2) -> str:
    matches = select_toolsets(query, limit=limit)
    if not matches:
        return "Nenhum toolset especifico selecionado."
    rows = []
    for item in matches:
        capabilities = ", ".join(str(value) for value in item.get("capabilities", [])[:3])
        risks = ", ".join(str(value) for value in item.get("risks", [])[:2])
        rows.append(
            f"{item['title']} ({item['name']}): capacidades {capabilities}; riscos {risks}; politica {item['default_model_policy']}"
        )
    return "Toolsets relevantes: " + " | ".join(rows)
