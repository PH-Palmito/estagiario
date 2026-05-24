from collections.abc import Callable

from memory.investment_formatting import format_brl

AskGrounded = Callable[..., dict | None]
GetStrategy = Callable[[str], dict]
AssetFundamentals = Callable[[dict], dict[str, dict]]
ExtractQuestionTicker = Callable[[str], str]
ExtractTicker = Callable[[dict], str]
SummarizeAssetNews = Callable[..., str | None]


def ask_grounded_investment_reading(
    question: str,
    snapshot: dict,
    *,
    gemini_api_key: str,
    ask_gemini_grounded_model: AskGrounded,
    get_asset_strategy: GetStrategy,
    asset_fundamentals: AssetFundamentals,
    extract_question_ticker: ExtractQuestionTicker,
    extract_ticker: ExtractTicker,
) -> str | None:
    if not gemini_api_key:
        return None

    metric_map = snapshot.get("metric_map") or {}
    ticker = extract_question_ticker(question) or extract_ticker(snapshot) or str(snapshot.get("page_title", "")).strip() or "ativo não identificado"
    summary = str(snapshot.get("summary", "")).strip() or "sem resumo salvo"
    lines = [str(item).strip() for item in (snapshot.get("lines") or []) if str(item).strip()][:12]
    metrics = "; ".join(f"{key}: {value}" for key, value in metric_map.items() if value) or "nenhuma métrica estruturada"
    strategy = get_asset_strategy(ticker)
    fundamentals = asset_fundamentals(snapshot).get(ticker, {})
    strategy_context = []
    if strategy.get("price_ceiling") is not None:
        strategy_context.append(f"preço-teto: {format_brl(strategy['price_ceiling'])}")
    if strategy.get("in_watchlist"):
        strategy_context.append("está na watchlist")
    if strategy.get("thesis"):
        strategy_context.append(f"tese: {strategy['thesis']}")
    if fundamentals.get("dividend_yield_current"):
        strategy_context.append(f"DY atual salvo: {fundamentals['dividend_yield_current']}")
    if fundamentals.get("dividend_yield_5y_average"):
        strategy_context.append(f"DY médio 5 anos salvo: {fundamentals['dividend_yield_5y_average']}")

    prompt = (
        "Você é o Axel respondendo uma pergunta sobre investimentos usando um snapshot local e, se necessário, busca web atual.\n"
        "Responda em português do Brasil, de forma útil, clara e cautelosa.\n"
        "Não cite links nem fontes a menos que o usuário peça.\n"
        "Não dê recomendação categórica de compra ou venda como certeza.\n"
        "Prefira uma leitura prática: momento do ativo, principais riscos, o que observar e se o cenário parece mais favorável ou mais exigente.\n"
        "Se faltar dado para concluir com força, diga isso de forma natural.\n"
        "Pode responder em 4 a 6 frases.\n\n"
        f"Ativo ou contexto principal: {ticker}\n"
        f"Resumo local salvo: {summary}\n"
        f"Métricas locais salvas: {metrics}\n"
        f"Contexto estratégico do Pedro: {'; '.join(strategy_context) if strategy_context else 'nenhuma regra pessoal salva para esse ativo'}\n"
        "Trechos locais úteis:\n"
        + ("\n".join(f"- {line}" for line in lines) if lines else "- nenhum trecho extra salvo")
        + f"\n\nPergunta do Pedro:\n{question}\n\nResposta:"
    )
    try:
        result = ask_gemini_grounded_model(
            prompt,
            timeout_seconds=25,
            max_output_tokens=320,
            temperature=0.2,
        )
        text = str((result or {}).get("text", "")).strip()
        if text:
            return text
    except Exception:
        return None
    return None


def ask_grounded_asset_news(
    question: str,
    ticker: str,
    *,
    gemini_api_key: str,
    ask_gemini_grounded_model: AskGrounded,
    get_asset_strategy: GetStrategy,
) -> str | None:
    if not gemini_api_key:
        return None

    strategy = get_asset_strategy(ticker)
    thesis = str(strategy.get("thesis", "")).strip()
    prompt = (
        "Você é o Axel, assistente financeiro pessoal do Pedro Henrique.\n"
        f"Ativo: {ticker}\n"
        f"Tese salva: {thesis or 'não informada'}\n"
        f"Pergunta: {question}\n\n"
        "Pesquise notícias, fatos relevantes, comunicados, dividendos anunciados ou eventos recentes que afetem esse ativo.\n"
        "Responda em português do Brasil.\n"
        "Seja prático e útil.\n"
        "Diga o que realmente importa para o investidor.\n"
        "Se houver mais de um ponto importante, resuma em até 4 frases curtas.\n"
        "Não cite links nem fontes a menos que isso seja pedido.\n"
        "Se não encontrar nada realmente relevante, diga isso claramente."
    )
    try:
        result = ask_gemini_grounded_model(
            prompt,
            timeout_seconds=30,
            max_output_tokens=320,
            temperature=0.2,
        )
        text = str((result or {}).get("text", "")).strip()
        if text and len(text) >= 60 and any(punct in text for punct in ".!?"):
            return text
    except Exception:
        return None
    return None


def asset_news_answer(
    question: str,
    ticker: str,
    snapshot: dict,
    fundamentals: dict | None = None,
    *,
    get_asset_strategy: GetStrategy,
    summarize_asset_news: SummarizeAssetNews,
    ask_grounded_asset_news_fn: Callable[[str, str, dict], str | None],
) -> str | None:
    fundamentals = fundamentals or {}
    strategy = get_asset_strategy(ticker)
    company_name = str(fundamentals.get("company_name") or "").strip()
    thesis = str(strategy.get("thesis") or "").strip()

    try:
        api_summary = summarize_asset_news(
            ticker,
            company_name=company_name,
            thesis=thesis,
            market_data=fundamentals,
        )
        if api_summary:
            return api_summary
    except Exception:
        pass

    grounded_news = ask_grounded_asset_news_fn(question, ticker, snapshot)
    if grounded_news:
        return grounded_news
    return None
