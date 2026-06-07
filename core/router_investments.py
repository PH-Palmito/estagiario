from __future__ import annotations

import re

from core.router_utils import normalize_text


def detect_investment_browser_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {
        "atualizar carteira em segundo plano",
        "atualizar investimentos em segundo plano",
        "sincronizar carteira em segundo plano",
        "sincronizar investimentos em segundo plano",
        "atualizar carteira no background",
    }:
        return {"intent": "background_investment_refresh", "target": None}

    if lower in {
        "atualizar investimentos",
        "atualizar meus investimentos",
        "atualizar carteira",
        "sincronizar investimentos",
        "sincronizar carteira",
        "reler carteira",
        "ler carteira agora",
        "analisar investimentos",
        "analisar meus investimentos",
        "resumir investimentos",
        "resuma investimentos",
        "analisar carteira",
        "ler carteira",
    }:
        return {"intent": "investment_refresh_public_wallet", "target": None}

    if lower in {
        "modo investimentos",
        "resumo financeiro",
        "resumo da carteira",
        "minha carteira",
        "ver investimentos",
        "acompanhar investimentos",
        "acompanhar carteira",
        "ver carteira",
        "resumir carteira",
    }:
        return {"intent": "investment_memory_summary", "target": None}

    if lower in {
        "valor investido",
        "valor investido da carteira",
        "valor atual",
        "valor atual da carteira",
        "patrimonio",
        "rentabilidade",
        "rentabilidade da carteira",
        "proventos",
        "proventos da carteira",
        "dividendos",
        "dividendos da carteira",
        "lucro",
        "prejuizo",
        "saldo da carteira",
        "posicoes",
    }:
        return {"intent": "investment_memory_answer", "target": user_input.strip()}

    if lower in {
        "abrir investidor 10",
        "abrir investidor10",
        "abrir carteira",
        "abrir minha carteira",
        "abrir carteira do investidor 10",
        "abrir carteira do investidor10",
        "abrir meus investimentos",
        "abrir carteira e resumir",
        "abrir minha carteira e resumir",
        "abrir carteira e analisar",
        "abrir minha carteira e analisar",
        "abrir investidor 10 e resumir",
        "abrir investidor10 e resumir",
        "abrir investidor 10 e analisar",
        "abrir investidor10 e analisar",
    }:
        return {"intent": "browser_open_wallet_and_summarize", "target": None}

    return None


def detect_investment_question_command(user_input: str):
    lower = normalize_text(user_input)
    if not lower:
        return None

    if lower in {
        "relatorio financeiro em segundo plano",
        "relatorio da carteira em segundo plano",
        "gerar relatorio financeiro em segundo plano",
        "gerar relatorio da carteira em segundo plano",
        "relatorio financeiro no background",
    }:
        return {"intent": "background_investment_report", "target": None}

    if any(
        phrase in lower
        for phrase in {
            "o que mudou na carteira desde ontem",
            "oque mudou na carteira desde ontem",
            "resumo diario da carteira",
            "resumo diário da carteira",
            "mudancas da carteira desde ontem",
            "mudanças da carteira desde ontem",
            "mudou na carteira desde ontem",
            "carteira desde ontem",
            "relatorio diario da carteira",
            "relatório diário da carteira",
            "resumo de ontem da carteira",
        }
    ):
        return {"intent": "investment_daily_report", "target": None}

    if any(
        phrase in lower
        for phrase in {
            "relatorio financeiro",
            "relatorio da carteira",
            "relatorio consolidado",
            "gerar relatorio",
            "fechar relatorio financeiro",
        }
    ):
        return {"intent": "investment_financial_report", "target": None}

    if lower in {
        "monitor da carteira",
        "monitor proativo da carteira",
        "radar proativo da carteira",
        "rodar monitor da carteira",
        "checar alertas da carteira",
    }:
        return {"intent": "investment_portfolio_monitor", "target": None}

    investment_terms = {
        "patrimonio",
        "valor investido",
        "valor atual",
        "rentabilidade",
        "proventos",
        "dividendos",
        "lucro",
        "prejuizo",
        "aporte",
        "cotacao",
        "preco medio",
        "carteira",
        "investimentos",
        "rendeu",
        "retorno",
        "watchlist",
        "ativo",
        "ativos",
        "posicao",
        "posicoes",
        "criterio",
        "margem de seguranca",
        "merecem atencao",
        "noticia",
        "noticias",
        "fato relevante",
        "fatos relevantes",
        "agenda de dividendos",
        "dividendos agendados",
        "proximo dividendo",
        "data ex",
        "data com",
        "monitoramento",
        "radar da carteira",
        "fii",
        "fiis",
        "fundo imobiliario",
        "fundos imobiliarios",
    }
    investment_opinion_terms = {
        "vale a pena",
        "bom ativo",
        "ativo bom",
        "esta bom",
        "esta ruim",
        "subindo",
        "caindo",
        "tendencia",
        "cenario",
        "avaliacao",
        "analise",
        "opiniao",
        "risco",
        "riscos",
        "tese",
        "comprar",
        "vender",
        "barato",
        "caro",
        "preco teto",
    }
    question_starters = (
        "qual ",
        "quanto ",
        "quais ",
        "como ",
        "me diga ",
        "me fala ",
        "me fale ",
        "mostrar ",
        "mostre ",
        "o que ",
        "vale ",
        "tem ",
        "agenda ",
        "monitoramento",
        "monitorar ",
        "proximo ",
        "houve ",
    )
    has_ticker = bool(re.search(r"\b[a-z]{4}\d{1,2}\b", lower))

    if "carteira" in lower and any(term in lower for term in {"noticia", "noticias", "fato relevante", "fatos relevantes"}):
        return {"intent": "investment_memory_answer", "target": user_input.strip()}

    if any(term in lower for term in investment_terms) and (
        lower.startswith(question_starters) or "?" in user_input
    ):
        return {"intent": "investment_memory_answer", "target": user_input.strip()}

    if lower in investment_terms:
        return {"intent": "investment_memory_answer", "target": user_input.strip()}

    if has_ticker and (
        lower.startswith(question_starters)
        or any(term in lower for term in investment_opinion_terms)
        or "?" in user_input
    ):
        return {"intent": "investment_memory_answer", "target": user_input.strip()}

    return None


def detect_investment_strategy_command(user_input: str):
    lower = normalize_text(user_input)
    if not lower:
        return None

    price_match = re.search(r"\b([a-z]{4}\d{1,2})\b", lower)
    value_match = re.search(r"(?:em|por|ate|até)\s+(\d+(?:[.,]\d{1,2})?)", user_input, flags=re.I)
    if not value_match:
        value_match = re.search(r"\b(\d+(?:[.,]\d{1,2})?)\b", user_input)
    if (
        any(term in lower for term in {"defina", "definir", "salve", "salvar", "colocar", "setar"})
        and "teto" in lower
        and ("preco" in lower.replace(" ", "") or "pre o" in lower or "preco teto" in lower)
        and price_match
        and value_match
    ):
        return {
            "intent": "investment_set_price_ceiling",
            "ticker": price_match.group(1).upper(),
            "price": value_match.group(1),
        }

    margin_match = re.search(r"(?:margem\s+de\s+seguranca|margem\s+de\s+segurança).{0,12}?(\d+(?:[.,]\d{1,2})?)", user_input, flags=re.I)
    if margin_match and (
        any(term in lower for term in {"definir", "salvar", "ajustar", "mudar", "colocar", "setar"})
        or "automatica" in lower
        or "automatico" in lower
    ):
        return {
            "intent": "investment_set_auto_ceiling_margin",
            "value": margin_match.group(1),
        }

    if lower in {
        "qual minha margem de seguranca",
        "margem de seguranca",
        "qual a margem de seguranca",
        "status do preco teto automatico",
    }:
        return {"intent": "investment_get_auto_ceiling_settings", "target": None}

    match = re.search(
        r"(?:adicione|adicionar|coloque|colocar|inclua|incluir)\s+([a-z]{3,5}\d{0,2})(?:[-/](?:brl|usd|usdt))?\s+(?:na|a\s+na)?\s*watchlist",
        lower,
    )
    if match:
        return {"intent": "investment_add_watchlist", "ticker": match.group(1).upper()}

    match = re.search(
        r"(?:remova|remover|tire|tirar|exclua|excluir)\s+([a-z]{3,5}\d{0,2})(?:[-/](?:brl|usd|usdt))?\s+(?:da|da\s+minha|da\s+watchlist)?",
        lower,
    )
    if match and "watchlist" in lower:
        return {"intent": "investment_remove_watchlist", "ticker": match.group(1).upper()}

    match = re.search(
        r"(?:defina|definir|salve|salvar|anote|anotar)\s+tese\s+(?:de|da|para)?\s*([a-z]{4}\d{1,2})\s*(?:como|:)?\s*(.+)$",
        user_input.strip(),
        flags=re.I,
    )
    if match:
        thesis = match.group(2).strip(" .")
        if thesis:
            return {
                "intent": "investment_set_thesis",
                "ticker": match.group(1).upper(),
                "thesis": thesis,
            }

    if lower in {
        "watchlist",
        "minha watchlist",
        "listar watchlist",
        "liste watchlist",
        "listar minha watchlist",
        "liste minha watchlist",
        "lista de ativos",
        "lista da watchlist",
    }:
        return {"intent": "investment_list_watchlist", "target": None}

    return None


INVESTMENT_STRATEGY_DETECTORS = [
    detect_investment_strategy_command,
]

INVESTMENT_BROWSER_DETECTORS = [
    detect_investment_browser_command,
]

INVESTMENT_QUESTION_DETECTORS = [
    detect_investment_question_command,
]
