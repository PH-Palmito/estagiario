from typing import Callable

from memory.investment_formatting import format_brl, format_percent, parse_currency_value, parse_percent_value


ContainsPhrase = Callable[..., bool]


def answer_dividend_question(
    snapshot: dict,
    question_ticker: str,
    fundamentals: dict,
    *,
    ticker_dividend_events: Callable[[dict, str], list[dict]],
    format_dividend_event: Callable[[str, dict], str],
    portfolio_dividend_schedule_answer: Callable[[dict], str],
) -> str:
    if question_ticker:
        events = ticker_dividend_events(snapshot, question_ticker)
        if events:
            details = "; ".join(format_dividend_event(question_ticker, event) for event in events[:3])
            return f"Os proximos eventos de dividendos que encontrei para {question_ticker} sao: {details}."
        dy_current = str(fundamentals.get("dividend_yield_current") or "").strip()
        if dy_current:
            return (
                f"Ainda não encontrei uma próxima data de dividendo confiável para {question_ticker}. "
                f"O que eu já tenho salvo é um dividend yield atual de {dy_current}."
            )
        return f"Ainda nao encontrei uma agenda de dividendos confiavel para {question_ticker}."
    return portfolio_dividend_schedule_answer(snapshot)


def answer_portfolio_news_question(
    snapshot: dict,
    *,
    portfolio_news_digest: Callable[..., list[str]],
) -> str:
    news_items = portfolio_news_digest(
        snapshot,
        limit_assets=5,
        limit_summaries=3,
        only_new=True,
        mark_seen=True,
    )
    if news_items:
        return "Noticias novas que parecem mais uteis na carteira agora: " + " ".join(news_items)
    return "No momento, eu nao encontrei noticia nova, confiavel e especifica o bastante para a carteira."


def answer_ticker_yield(question_ticker: str, fundamentals: dict) -> str:
    current_dy = fundamentals.get("dividend_yield_current")
    average_dy = fundamentals.get("dividend_yield_5y_average")
    if current_dy and average_dy:
        return f"O DY atual de {question_ticker} está em {current_dy}, com média de 5 anos em {average_dy}."
    if current_dy:
        return f"O DY atual de {question_ticker} está em {current_dy}."
    return f"Ainda não tenho DY salvo para {question_ticker}."


def answer_ticker_quote(question_ticker: str, asset_position: dict, fundamentals: dict) -> str:
    current_price = asset_position.get("current_price") or fundamentals.get("quote")
    if current_price:
        rentability = asset_position.get("rentability")
        if rentability:
            return f"A cotação de {question_ticker} está em {current_price}. Sua rentabilidade está em {rentability}."
        return f"A cotação de {question_ticker} está em {current_price}."
    return f"Ainda não tenho cotação salva para {question_ticker}."


def answer_ticker_average_price(question_ticker: str, asset_position: dict) -> str:
    average_price = asset_position.get("average_price")
    if average_price:
        return f"O preço médio de {question_ticker} está em {average_price}."
    return f"Ainda não tenho preço médio salvo para {question_ticker}."


def answer_ticker_day_variation(question_ticker: str, asset_position: dict) -> str:
    variation = asset_position.get("variation")
    rentability = asset_position.get("rentability")
    if variation or rentability:
        parts = [f"Ainda não tenho uma fonte intradiária confiável para afirmar a variação do dia de {question_ticker}."]
        if variation:
            parts.append(f"No snapshot salvo da posição, a variação exibida está em {variation}.")
        if rentability:
            parts.append(f"Desde o seu preço médio, a rentabilidade está em {rentability}.")
        return " ".join(parts)
    return f"Ainda não tenho uma fonte confiável de variação do dia para {question_ticker}."


def answer_ticker_trend(question_ticker: str, asset_position: dict) -> str:
    variation = asset_position.get("variation")
    rentability = asset_position.get("rentability")
    if variation:
        variation_value = parse_percent_value(variation)
        if variation_value is not None:
            if variation_value > 0:
                response = f"No snapshot atual da posição, {question_ticker} aparece em alta, com variação de {variation}."
            elif variation_value < 0:
                response = f"No snapshot atual da posição, {question_ticker} aparece em queda, com variação de {variation}."
            else:
                response = f"No snapshot atual da posição, {question_ticker} aparece estável, com variação de {variation}."
            if rentability:
                response += f" Desde o seu preço médio, a rentabilidade está em {rentability}."
            return response
        return f"A variação visível de {question_ticker} está em {variation}."
    return f"Ainda não tenho variação salva para {question_ticker}."


def answer_auto_price_ceiling(
    snapshot: dict,
    question_ticker: str,
    asset_position: dict,
    strategy: dict,
    *,
    extract_current_price: Callable[[dict], float | None],
    effective_price_ceiling: Callable[[dict, str, dict], tuple[float | None, str]],
) -> str | None:
    current_price = parse_currency_value(asset_position.get("current_price")) if asset_position else extract_current_price(snapshot)
    manual_ceiling = strategy.get("price_ceiling")
    effective_ceiling, source = effective_price_ceiling(snapshot, question_ticker, asset_position or {})

    if manual_ceiling is not None or effective_ceiling is None:
        return None

    relation = ""
    if current_price is not None:
        relation = "abaixo" if current_price <= effective_ceiling else "acima"
    if source == "automatic_yield":
        prefix = (
            f"Ainda não tenho preço-teto manual salvo para {question_ticker}. "
            f"Pela sua base automática de yield alvo, o teto estimado fica em {format_brl(effective_ceiling)}."
        )
    else:
        prefix = (
            f"Ainda não tenho preço-teto manual salvo para {question_ticker}. "
            f"Pela sua base automática atual, o teto estimado fica em {format_brl(effective_ceiling)}."
        )
    if relation:
        return prefix + f" Na cotação visível, ele está {relation} desse nível."
    return prefix


def answer_assets_above_ceiling(
    snapshot: dict,
    *,
    portfolio_items_above_ceiling: Callable[[dict], list[dict]],
) -> str:
    items = portfolio_items_above_ceiling(snapshot)
    if not items:
        return "Nenhum ativo com preço-teto manual ou automático está acima do seu critério no snapshot atual."
    parts = []
    for item in items[:6]:
        source_label = "teto manual"
        if item.get("source") == "automatic_yield":
            source_label = "teto automático por yield"
        elif item.get("source") == "automatic":
            source_label = "teto automático"
        premium = format_percent(item.get("premium_percent"))
        parts.append(
            f"{item['ticker']} em {format_brl(item['current_price'])}, acima do {source_label} de {format_brl(item['ceiling'])} por cerca de {premium}"
        )
    return "Ativos acima do seu preço-teto no snapshot atual: " + "; ".join(parts) + "."
