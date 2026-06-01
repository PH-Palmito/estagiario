from __future__ import annotations

import re
import time

from core.router_utils import normalize_text
from memory.current_topic import load_current_topic
from memory.docs_context import docs_context_relevant
from memory.vision_history import last_vision_item

FACTUAL_QUESTION_PREFIXES = (
    "o que e ",
    "oq e ",
    "oque e ",
    "quem e ",
    "qual e ",
    "quais sao ",
    "como funciona ",
)


def _looks_like_standalone_factual_question(text: str) -> bool:
    if not text.startswith(FACTUAL_QUESTION_PREFIXES):
        return False
    visual_reference_terms = {
        "isso",
        "esse",
        "essa",
        "desse",
        "dessa",
        "tela",
        "pagina",
        "site",
        "imagem",
        "grafico",
        "foto",
        "print",
    }
    return not any(term in text for term in visual_reference_terms)


def detect_visual_question_command(user_input: str):
    lower = normalize_text(user_input)
    if not lower:
        return None

    if docs_context_relevant(user_input):
        return None

    if _looks_like_standalone_factual_question(lower):
        return None

    if re.search(r"\b[a-z]{4}\d{1,2}\b", lower):
        return None

    investment_skip_terms = {
        "carteira",
        "patrimonio",
        "valor investido",
        "rentabilidade",
        "dividendos",
        "proventos",
        "watchlist",
        "preco teto",
        "margem de seguranca",
        "ativo",
        "ativos",
        "posicao",
        "posicoes",
        "cotacao",
        "criterio",
    }
    if any(term in lower for term in investment_skip_terms):
        return None

    last_item = last_vision_item()
    current_topic = load_current_topic() or {}
    created_at = float(last_item.get("created_at", 0)) if isinstance(last_item, dict) else 0.0
    has_recent_visual_context = bool(last_item and (time.time() - created_at) <= 900)
    has_topic_context = bool(str(current_topic.get("topic", "")).strip() or str(current_topic.get("summary", "")).strip())

    conversational_followup_terms = (
        "e por que",
        "e porque",
        "por que",
        "porque",
        "e qual",
        "e quais",
        "e como",
        "e isso",
        "e agora",
        "mas por que",
        "voce acha",
        "vc acha",
        "acha que",
        "o que voce acha",
        "o que acha",
        "o que voce pensa",
        "o que pensa",
        "qual sua opiniao",
        "qual a sua opiniao",
        "me explica",
        "me explique",
        "me fala mais",
        "me fale mais",
        "fala mais",
        "fale mais",
        "me fala mais sobre isso",
        "me fale mais sobre isso",
        "explica",
        "explique",
        "detalha",
        "detalhar",
        "interpreta",
        "interprete",
        "tem melhores",
        "existem melhores",
        "existe melhor",
        "qual voce escolheria",
        "qual voce prefere",
        "recomenda",
        "recomendaria",
    )

    explicit_prefixes = (
        "perguntar sobre imagem ",
        "pergunta sobre imagem ",
        "perguntar sobre a imagem ",
        "pergunta sobre a imagem ",
        "perguntar sobre pagina ",
        "pergunta sobre pagina ",
        "perguntar sobre a pagina ",
        "pergunta sobre a pagina ",
        "perguntar sobre site ",
        "pergunta sobre site ",
        "perguntar sobre o site ",
        "pergunta sobre o site ",
        "perguntar sobre tela ",
        "pergunta sobre tela ",
        "perguntar sobre a tela ",
        "pergunta sobre a tela ",
        "perguntar sobre grafico ",
        "pergunta sobre grafico ",
        "perguntar sobre o grafico ",
        "pergunta sobre o grafico ",
        "sobre a imagem ",
        "sobre a pagina ",
        "sobre o site ",
        "sobre a tela ",
        "sobre o grafico ",
        "sobre essa imagem ",
        "sobre essa pagina ",
        "sobre essa tela ",
        "sobre esse grafico ",
    )
    for prefix in explicit_prefixes:
        if lower.startswith(prefix):
            question = user_input[len(prefix):].strip()
            if question:
                return {"intent": "vision_answer_question", "target": question}

    visual_terms = {"imagem", "grafico", "visual", "foto", "print", "tela", "pagina", "site"}
    chart_question_terms = {
        "ganhou",
        "venceu",
        "vencedor",
        "maior",
        "menor",
        "menos",
        "valor",
        "valores",
        "resultado",
        "quanto",
        "porcentagem",
        "percentual",
        "queda",
        "caiu",
        "variacao",
        "anos",
        "materia",
        "categoria",
        "categorias",
        "titulo",
        "assunto",
        "preco",
        "link",
        "repo",
        "repositorio",
    }
    question_starters = (
        "qual ",
        "quais ",
        "quem ",
        "que ",
        "quanto ",
        "quantos ",
        "quantas ",
        "o que ",
        "sobre o que ",
        "por que ",
        "porque ",
        "como ",
        "listar ",
        "lista ",
        "valor ",
        "valor de ",
        "quanto deu ",
        "quanto custa ",
        "quanto custa",
        "custa quanto ",
        "custa quanto",
        "resultado de ",
        "mostra ",
        "mostre ",
        "me explica ",
        "me explique ",
        "explica ",
        "explique ",
        "detalha ",
        "detalhar ",
        "interpreta ",
        "interprete ",
        "voce acha ",
        "vc acha ",
        "acha que ",
        "existem ",
        "existe ",
        "tem ",
    )

    compact_lower = lower.replace(" ", "")
    has_visual_term = any(term in lower for term in visual_terms) or "graf" in compact_lower
    has_chart_question = any(term in lower for term in chart_question_terms)
    contextless_chart_terms = {
        "ganhou",
        "venceu",
        "vencedor",
        "maior",
        "menor",
        "porcentagem",
        "percentual",
        "queda",
        "caiu",
        "variacao",
        "anos",
        "materia",
        "categoria",
        "titulo",
        "matematica",
        "portugues",
        "ciencias",
        "educacao fisica",
        "historia",
        "geografia",
        "ingles",
    }
    contextless_visual_terms = {
        "animal",
        "bicho",
        "objeto",
        "objetos",
        "pessoa",
        "pessoas",
        "cor",
        "cores",
        "texto",
        "escrito",
        "aparece",
        "mostra",
        "assunto",
        "resumo",
        "preco",
        "custa",
        "custo",
        "valor",
        "repositorio",
        "noticia",
        "pagina",
        "site",
        "isso",
        "essa",
        "esse",
        "dessa",
        "desse",
        "cenario",
    }
    has_contextless_chart_question = any(term in lower for term in contextless_chart_terms)
    has_contextless_visual_question = any(term in lower for term in contextless_visual_terms)
    starts_like_question = lower.startswith(question_starters)
    referential_context_terms = {
        "isso",
        "esse",
        "essa",
        "desse",
        "dessa",
        "tema",
        "assunto",
        "cenario",
        "pagina",
        "tela",
        "site",
        "grafico",
    }
    has_referential_context = any(term in lower for term in referential_context_terms)

    if has_visual_term and (has_chart_question or starts_like_question):
        return {"intent": "vision_answer_question", "target": user_input.strip()}

    if has_contextless_chart_question and starts_like_question:
        return {"intent": "vision_answer_question", "target": user_input.strip()}

    if has_contextless_visual_question and starts_like_question:
        return {"intent": "vision_answer_question", "target": user_input.strip()}

    if (last_item or has_topic_context) and lower.startswith(conversational_followup_terms):
        return {"intent": "vision_answer_question", "target": user_input.strip()}

    if (has_recent_visual_context or has_topic_context) and lower.startswith(question_starters) and has_referential_context:
        return {"intent": "vision_answer_question", "target": user_input.strip()}

    return None


def detect_vision_model_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {
        "status da visao",
        "status visao",
        "modelo visual",
        "modelo de visao",
        "status do modelo visual",
        "qual modelo visual",
        "visao local",
    }:
        return {"intent": "vision_status", "target": None}

    if lower in {
        "como ativar visao",
        "como instalar visao",
        "instalar modelo visual",
        "baixar modelo visual",
        "preparar visao",
    }:
        return {"intent": "vision_install_hint", "target": None}

    if lower in {
        "baixar moondream",
        "instalar moondream",
        "baixar modelo moondream",
        "baixar modelo visual leve",
        "instalar modelo visual leve",
    }:
        return {"intent": "vision_download_light_model", "target": None}

    if lower in {
        "modelo visual ativo",
        "qual modelo de visao",
    }:
        return {"intent": "vision_active_model", "target": None}

    if lower in {
        "historico visual",
        "ver historico visual",
        "mostrar historico visual",
        "ultimas analises visuais",
        "analises visuais recentes",
        "o que voce viu recentemente",
    }:
        return {"intent": "vision_history", "target": None}

    if lower in {
        "ultima analise visual",
        "ultima imagem analisada",
        "repetir analise visual",
        "o que voce viu na imagem",
    }:
        return {"intent": "vision_last_analysis", "target": None}

    return None


VISION_DETECTORS = [
    detect_visual_question_command,
    detect_vision_model_command,
]
