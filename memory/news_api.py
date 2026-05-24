from __future__ import annotations

import re
from collections import Counter
from datetime import UTC, datetime, timedelta

import requests

from config import GEMINI_API_KEY, NEWSAPI_ENABLED, NEWSAPI_KEY
from llm.gemini_client import ask_gemini_model

NEWSAPI_EVERYTHING_URL = "https://newsapi.org/v2/everything"
KNOWN_RELIABLE_SOURCES = {
    "valor econômico",
    "valor economico",
    "infomoney",
    "exame",
    "neofeed",
    "estadão",
    "estadao",
    "o globo",
    "g1",
    "cnn brasil",
    "reuters",
    "bloomberg",
    "money times",
    "istoé dinheiro",
    "istoe dinheiro",
    "seu dinheiro",
    "investing.com",
    "uol economia",
    "broadcast",
}
SENSATIONALIST_TERMS = {
    "urgente",
    "explosivo",
    "colapso",
    "derrete",
    "dispara",
    "despenca",
    "bomba",
    "chocante",
    "absurdo",
    "pânico",
    "panico",
    "milionário",
    "milionario",
    "imperdível",
    "imperdivel",
}
IMPACT_TERMS = {
    "alta",
    "queda",
    "cai",
    "sube",
    "sobe",
    "dispara",
    "despenca",
    "resultado",
    "lucro",
    "prejuízo",
    "prejuizo",
    "dividendo",
    "provento",
    "guidance",
    "aquisição",
    "aquisicao",
    "fusão",
    "fusao",
    "oferta",
    "captação",
    "captacao",
    "juros",
    "selic",
}
ACTIONABLE_TERMS = {
    "resultado",
    "lucro",
    "prejuízo",
    "prejuizo",
    "dividendo",
    "provento",
    "jcp",
    "guidance",
    "aquisição",
    "aquisicao",
    "fusão",
    "fusao",
    "oferta",
    "captação",
    "captacao",
    "fato relevante",
    "comunicado",
    "assembleia",
    "governança",
    "governanca",
    "regulação",
    "regulacao",
    "processo",
    "fraude",
    "dívida",
    "divida",
    "vacância",
    "vacancia",
    "volatilidade",
    "etf",
    "halving",
    "fed",
    "sec",
    "juros",
}
CRYPTO_ALIASES = {
    "BTC": ("bitcoin", "btc"),
    "ETH": ("ethereum", "ether", "eth"),
    "SOL": ("solana", "sol"),
    "BNB": ("bnb", "binance coin"),
    "XRP": ("xrp", "ripple"),
    "ADA": ("cardano", "ada"),
    "DOGE": ("dogecoin", "doge"),
}
GENERIC_ROUNDUP_TERMS = {
    "e mais ações",
    "e mais acoes",
    "ações para acompanhar",
    "acoes para acompanhar",
    "destaques do noticiário corporativo",
    "destaques do noticiario corporativo",
    "ações recomendadas para investir",
    "acoes recomendadas para investir",
    "o que esperar do mercado",
    "mercado hoje",
    "bolsa hoje",
    "criptomoedas hoje",
    "mercado cripto",
    "preco do bitcoin hoje",
    "preço do bitcoin hoje",
}


def _http_session() -> requests.Session:
    session = requests.Session()
    session.trust_env = False
    return session


def _iso_days_ago(days: int) -> str:
    target = datetime.now(UTC) - timedelta(days=days)
    return target.strftime("%Y-%m-%d")


def _normalize(text: str) -> str:
    lowered = str(text or "").strip().lower()
    lowered = re.sub(r"[^\w\s%$.,:-]", " ", lowered)
    lowered = re.sub(r"\s+", " ", lowered)
    return lowered.strip()


def _build_query(ticker: str, company_name: str = "") -> str:
    normalized_ticker = ticker.upper().strip()
    crypto_aliases = CRYPTO_ALIASES.get(normalized_ticker, ())
    if crypto_aliases:
        terms = " OR ".join(f'"{term}"' for term in crypto_aliases)
        return f"({terms})"
    ticker_term = f'"{normalized_ticker}"'
    company_term = f'"{company_name.strip()}"' if company_name.strip() else ""
    if company_term:
        return f"({ticker_term} OR {company_term})"
    return ticker_term


def fetch_asset_news(ticker: str, company_name: str = "", days_back: int = 7, page_size: int = 8) -> list[dict]:
    if not NEWSAPI_ENABLED or not NEWSAPI_KEY:
        return []

    session = _http_session()
    response = session.get(
        NEWSAPI_EVERYTHING_URL,
        params={
            "q": _build_query(ticker, company_name),
            "language": "pt",
            "sortBy": "publishedAt",
            "from": _iso_days_ago(days_back),
            "pageSize": max(1, min(int(page_size), 20)),
        },
        headers={"X-Api-Key": NEWSAPI_KEY},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json() or {}
    articles = payload.get("articles") or []
    cleaned = []
    for article in articles:
        title = str(article.get("title", "")).strip()
        description = str(article.get("description", "")).strip()
        if not title:
            continue
        cleaned.append(
            {
                "title": title,
                "description": description,
                "source": str((article.get("source") or {}).get("name", "")).strip(),
                "url": str(article.get("url", "")).strip(),
                "published_at": str(article.get("publishedAt", "")).strip(),
            }
        )
    return cleaned


def _theme_signature(title: str, description: str) -> str:
    text = _normalize(f"{title} {description}")
    tokens = re.findall(r"\b[a-zà-ÿ0-9]{4,}\b", text)
    stopwords = {
        "sobre",
        "entre",
        "para",
        "com",
        "pela",
        "pelo",
        "após",
        "apos",
        "hoje",
        "ontem",
        "depois",
        "mercado",
        "ações",
        "acoes",
        "empresa",
        "ativo",
        "ativos",
        "brasil",
    }
    filtered = [token for token in tokens if token not in stopwords][:6]
    return "|".join(filtered)


def _clean_description(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    cleaned = re.sub(r"The post .*?$", "", cleaned, flags=re.IGNORECASE).strip()
    cleaned = re.sub(r"R\$\s*(\d+(?:[.,]\d+)?)\s*((?:bilh|milh)\w+|mil)\b", r"\1 \2 de reais", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"R\$(\d)", r"R$ \1", cleaned)
    return cleaned.rstrip(". ")


def _trim_title(title: str, ticker: str, company_name: str = "") -> str:
    cleaned = re.sub(r"\s+", " ", str(title or "")).strip().rstrip(".")
    if not cleaned:
        return ""
    ticker_text = str(ticker or "").strip()
    if ticker_text:
        cleaned = re.sub(rf"\(\s*{re.escape(ticker_text)}\s*\)", "", cleaned, flags=re.I)
        cleaned = re.sub(rf"\b{re.escape(ticker_text)}\b\s*[:-]?\s*", "", cleaned, count=1, flags=re.I)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -,:;")
    return cleaned


def _market_confirms_impact(text: str, market_data: dict) -> bool | None:
    normalized = _normalize(text)
    change_percent = market_data.get("regular_market_change_percent")
    volume = market_data.get("regular_market_volume")
    if change_percent is None:
        return None

    if any(term in normalized for term in {"alta", "sube", "sobe", "dispara"}):
        return float(change_percent) > 0.5
    if any(term in normalized for term in {"queda", "cai", "despenca", "derrete"}):
        return float(change_percent) < -0.5
    if "volume" in normalized and volume is not None:
        return True
    return None


def classify_news_articles(
    articles: list[dict],
    market_data: dict | None = None,
    ticker: str = "",
    company_name: str = "",
) -> list[dict]:
    market_data = market_data or {}
    ticker_normalized = _normalize(ticker)
    company_normalized = _normalize(company_name)
    crypto_aliases = tuple(_normalize(item) for item in CRYPTO_ALIASES.get(str(ticker or "").upper(), ()))
    theme_counts = Counter(
        _theme_signature(article.get("title", ""), article.get("description", ""))
        for article in articles
        if article.get("title")
    )
    results = []

    for article in articles:
        title = str(article.get("title", "")).strip()
        description = str(article.get("description", "")).strip()
        source = str(article.get("source", "")).strip()
        published_at = str(article.get("published_at", "")).strip()
        text = f"{title} {description}"
        normalized = _normalize(text)

        score = 0.35
        reasons = []

        direct_mention = False
        if ticker_normalized and ticker_normalized in normalized:
            direct_mention = True
        if company_normalized and company_normalized in normalized:
            direct_mention = True
        if crypto_aliases and any(alias in normalized for alias in crypto_aliases):
            direct_mention = True
        if direct_mention:
            score += 0.18
            reasons.append("ligação direta com o ativo")
        else:
            score -= 0.16
            reasons.append("ligação fraca com o ativo")

        if any(term in normalized for term in GENERIC_ROUNDUP_TERMS):
            score -= 0.26
            reasons.append("matéria ampla demais para o ativo")

        source_normalized = _normalize(source)
        if source_normalized in KNOWN_RELIABLE_SOURCES:
            score += 0.22
            reasons.append("fonte conhecida")
        elif source_normalized:
            score -= 0.08
            reasons.append("fonte pouco conhecida")
        else:
            score -= 0.12
            reasons.append("fonte indefinida")

        signature = _theme_signature(title, description)
        redundancy_count = theme_counts.get(signature, 0)
        if redundancy_count >= 2:
            score += 0.18
            reasons.append("tema confirmado por múltiplas fontes")
        else:
            score -= 0.12
            reasons.append("tema sem confirmação ampla")

        sensational_hits = [term for term in SENSATIONALIST_TERMS if term in normalized]
        factual_hits = 0
        if re.search(r"\b\d+[,.]?\d*%?\b", text):
            factual_hits += 1
        if re.search(r"\b\d{4}\b", text):
            factual_hits += 1
        if published_at:
            factual_hits += 1
        impact_hits = [term for term in IMPACT_TERMS if term in normalized]
        actionable_hits = [term for term in ACTIONABLE_TERMS if term in normalized]
        if impact_hits:
            factual_hits += 1
        if actionable_hits:
            factual_hits += 1

        if sensational_hits and factual_hits <= 1:
            score -= 0.35
            reasons.append("linguagem emocional sem base factual suficiente")
        elif sensational_hits:
            score -= 0.12
            reasons.append("linguagem exagerada")

        if factual_hits >= 3:
            score += 0.18
            reasons.append("há dados e elementos concretos")
        elif factual_hits == 2:
            score += 0.08
            reasons.append("há algum lastro factual")
        else:
            score -= 0.14
            reasons.append("faltam dados concretos")

        market_check = _market_confirms_impact(text, market_data)
        if market_check is True:
            score += 0.12
            reasons.append("movimento compatível com os dados de mercado")
        elif market_check is False:
            score -= 0.18
            reasons.append("impacto não confirmado pelos dados de mercado")

        is_crypto = bool(crypto_aliases)
        is_generic_crypto = is_crypto and any(
            term in normalized
            for term in {
                "criptomoedas",
                "mercado cripto",
                "mercado de cripto",
                "preco do bitcoin hoje",
                "preço do bitcoin hoje",
            }
        )
        if is_crypto and not actionable_hits and not re.search(r"\b(etf|sec|fed|halving|regula\w+|juros|liquida\w+|fluxo|reserva|tesouro)\b", normalized):
            score -= 0.22
            reasons.append("cripto sem gatilho acionável")
        if is_generic_crypto and not actionable_hits:
            score -= 0.20
            reasons.append("matéria ampla de cripto")

        score = max(0.0, min(1.0, round(score, 2)))

        if sensational_hits and factual_hits <= 1:
            classification = "SENSACIONALISTA"
        elif score >= 0.68 and (actionable_hits or not is_crypto):
            classification = "RELEVANTE"
        else:
            classification = "IRRELEVANTE"

        results.append(
            {
                "title": title,
                "classificacao": classification,
                "score": score,
                "motivo": "; ".join(reasons[:4]),
                "source": source,
                "published_at": published_at,
                "description": description,
            }
        )

    return results


def summarize_asset_news(
    ticker: str,
    company_name: str = "",
    thesis: str = "",
    market_data: dict | None = None,
) -> str | None:
    articles = fetch_asset_news(ticker, company_name=company_name)
    if not articles:
        return None

    classified = classify_news_articles(
        articles,
        market_data=market_data,
        ticker=ticker,
        company_name=company_name,
    )
    relevant = [item for item in classified if item["classificacao"] == "RELEVANTE"]
    non_sensational = [item for item in classified if item["classificacao"] != "SENSACIONALISTA"]

    if GEMINI_API_KEY and relevant:
        snippets = []
        for article in relevant[:4]:
            description = article["description"] or "sem descrição útil"
            snippets.append(
                f"- {article['title']} | {description} | score {article['score']} | motivo: {article['motivo']}"
            )
        prompt = (
            "Você é o Axel resumindo notícias para um investidor pessoa física.\n"
            f"Ativo: {ticker}\n"
            f"Empresa: {company_name or 'não informada'}\n"
            f"Tese salva: {thesis or 'não informada'}\n\n"
            "Resuma apenas o que parece relevante e confiável.\n"
            "Responda em português do Brasil, em 3 ou 4 frases curtas.\n"
            "Não cite links. Não liste fontes. Foque em impacto prático, risco, dividendos, resultados, setor ou governança.\n"
            "Se o material ainda estiver fraco ou inconclusivo, diga isso de forma honesta.\n\n"
            "Notícias classificadas como relevantes:\n"
            + "\n".join(snippets)
            + "\n\nResposta:"
        )
        try:
            answer = ask_gemini_model(
                prompt,
                timeout_seconds=20,
                max_output_tokens=220,
                temperature=0.2,
            ).strip()
            if answer and len(answer) >= 60 and any(punct in answer for punct in ".!?"):
                return answer
        except Exception:
            pass

    if relevant:
        highlights = []
        for item in relevant[:2]:
            title = _trim_title(item["title"], ticker, company_name=company_name)
            description = _clean_description(item.get("description") or "")
            explanation = description.rstrip(".")
            if explanation:
                highlights.append(f"{title}. Isso importa porque {explanation[:180].rstrip('.')}.")
            else:
                highlights.append(f"{title}. Motivo principal: {item['motivo']}.")
        return f"Encontrei sinais relevantes sobre {ticker}. " + " ".join(highlights)

    if non_sensational:
        return f"Eu encontrei material sobre {ticker}, mas nada com confiança suficiente para tratar como realmente relevante por enquanto."

    return f"O que apareceu sobre {ticker} parece fraco ou sensacionalista demais para eu tratar como sinal confiável."


def analyze_asset_news(
    ticker: str,
    company_name: str = "",
    market_data: dict | None = None,
) -> list[dict]:
    articles = fetch_asset_news(ticker, company_name=company_name)
    if not articles:
        return []
    return classify_news_articles(
        articles,
        market_data=market_data,
        ticker=ticker,
        company_name=company_name,
    )
