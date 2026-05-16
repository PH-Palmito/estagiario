from typing import Callable

from memory.investment_formatting import format_brl, parse_currency_value


GetStrategy = Callable[[str], dict]
AssetFundamentals = Callable[[dict], dict[str, dict]]
AssetPositions = Callable[[dict], dict[str, dict]]
ExtractTicker = Callable[[dict], str]
ExtractQuestionTicker = Callable[[str], str]
ExtractDirection = Callable[[dict], str]
EffectiveCeiling = Callable[[dict, str, dict], tuple[float | None, str]]
MentionsPriceCeiling = Callable[[str], bool]
Normalize = Callable[[str], str]
QuickOpinion = Callable[[dict, str, dict], str]
ActionStance = Callable[[dict, str, dict], str]
ExtractCurrentPrice = Callable[[dict], float | None]


def format_position_reading(
    snapshot: dict,
    ticker: str,
    position: dict,
    *,
    get_asset_strategy: GetStrategy,
    asset_fundamentals: AssetFundamentals,
    effective_price_ceiling: EffectiveCeiling,
    position_quick_opinion: QuickOpinion,
    position_action_stance: ActionStance,
) -> str:
    strategy = get_asset_strategy(ticker)
    fundamentals = asset_fundamentals(snapshot).get(ticker, {})
    current_price_text = str(position.get("current_price") or fundamentals.get("quote") or "").strip()
    current_price_value = parse_currency_value(current_price_text)
    parts = [
        f"Sobre {ticker}, a cotação atual está em {current_price_text or 'valor não identificado'}.",
    ]

    if position.get("average_price"):
        parts.append(f"Seu preço médio está em {position['average_price']}.")
    if position.get("variation"):
        parts.append(f"A variação no recorte está em {position['variation']}.")
    if position.get("rentability"):
        parts.append(f"A rentabilidade mostrada está em {position['rentability']}.")
    if position.get("balance"):
        parts.append(f"O saldo atual visível é {position['balance']}.")
    if position.get("portfolio_percentage"):
        parts.append(f"Hoje ele representa {position['portfolio_percentage']} da carteira.")
    if fundamentals.get("dividend_yield_current"):
        parts.append(f"O dividend yield atual salvo está em {fundamentals['dividend_yield_current']}.")

    ceiling = strategy.get("price_ceiling")
    if ceiling is not None:
        parts.append(f"Seu preço-teto salvo para {ticker} é {format_brl(float(ceiling))}.")
        if current_price_value is not None:
            relation = "abaixo" if current_price_value <= float(ceiling) else "acima"
            parts.append(f"Pela cotação visível, ele está {relation} desse nível.")
    else:
        auto_ceiling, source = effective_price_ceiling(snapshot, ticker, position)
        if auto_ceiling is not None:
            if source == "automatic_yield":
                target_yield = float(strategy.get("auto_ceiling_target_yield_percent", 8.0))
                parts.append(
                    f"Pela base automática por yield alvo de {target_yield:.0f}%, "
                    f"o preço-teto estimado ficaria em {format_brl(auto_ceiling)}."
                )
            elif source == "automatic":
                margin = float(strategy.get("auto_ceiling_margin_percent", 8.0))
                parts.append(
                    f"Como referência automática, com margem de segurança de {margin:.0f}%, "
                    f"o preço-teto estimado ficaria em {format_brl(auto_ceiling)}."
                )

    thesis = str(strategy.get("thesis", "")).strip()
    if thesis:
        parts.append(f"Sua tese curta salva para esse ativo é: {thesis}")

    if strategy.get("in_watchlist"):
        parts.append(f"{ticker} já está na sua watchlist.")

    parts.append(position_quick_opinion(snapshot, ticker, position))
    parts.append(position_action_stance(snapshot, ticker, position))
    return " ".join(parts)


def build_local_investment_reading(
    question: str,
    snapshot: dict,
    *,
    get_asset_strategy: GetStrategy,
    asset_positions: AssetPositions,
    asset_fundamentals: AssetFundamentals,
    extract_question_ticker: ExtractQuestionTicker,
    extract_ticker: ExtractTicker,
    extract_snapshot_direction: ExtractDirection,
    extract_current_price: ExtractCurrentPrice,
    normalize: Normalize,
    mentions_price_ceiling: MentionsPriceCeiling,
    effective_price_ceiling: EffectiveCeiling,
) -> str:
    metric_map = snapshot.get("metric_map") or {}
    ticker = extract_question_ticker(question) or extract_ticker(snapshot)
    direction = extract_snapshot_direction(snapshot)
    summary = str(snapshot.get("summary", "")).strip()
    normalized_question = normalize(question)
    strategy = get_asset_strategy(ticker) if ticker else {}
    price_ceiling = strategy.get("price_ceiling")
    thesis = str(strategy.get("thesis", "")).strip()
    in_watchlist = bool(strategy.get("in_watchlist"))
    current_price = extract_current_price(snapshot)
    position = asset_positions(snapshot).get(ticker, {}) if ticker else {}
    fundamentals = asset_fundamentals(snapshot).get(ticker, {}) if ticker else {}

    asset_name = ticker or str(snapshot.get("page_title", "")).strip() or "esse ativo"
    parts = [f"Sobre {asset_name}, eu tenho um contexto recente de cotação, rentabilidade e proventos na sua carteira."]

    if direction:
        parts.append(f"No recorte visível, ele está {direction}.")

    if metric_map.get("rentabilidade"):
        parts.append(f"A rentabilidade destacada está em {metric_map['rentabilidade']}.")
    elif metric_map.get("variacao"):
        parts.append(f"A variação visível está em {metric_map['variacao']}.")

    if fundamentals.get("dividend_yield_current"):
        parts.append(f"O dividend yield atual salvo está em {fundamentals['dividend_yield_current']}.")

    if metric_map.get("proventos"):
        parts.append(f"Também há destaque para proventos, com referência visível a {metric_map['proventos']}.")

    if price_ceiling is not None:
        parts.append(f"Seu preço-teto salvo para {asset_name} é {format_brl(price_ceiling)}.")
        if current_price is not None:
            if current_price <= float(price_ceiling):
                parts.append("Pelo preço visível, ele está no ponto ou abaixo do seu preço-teto.")
            else:
                parts.append("Pelo preço visível, ele ainda está acima do seu preço-teto.")
    elif ticker and (current_price is not None or position):
        auto_ceiling, auto_source = effective_price_ceiling(snapshot, ticker, position or {"current_price": format_brl(current_price)})
        if auto_ceiling is not None:
            if auto_source == "automatic_yield":
                parts.append(
                    f"Pela base automática por yield alvo de {float(strategy.get('auto_ceiling_target_yield_percent', 8.0)):.0f}%, "
                    f"o preço-teto estimado ficaria em {format_brl(auto_ceiling)}."
                )
            else:
                parts.append(
                    f"Como referência automática provisória, com margem de segurança de "
                    f"{float(strategy.get('auto_ceiling_margin_percent', 8.0)):.0f}%, "
                    f"o preço-teto estimado ficaria em {format_brl(auto_ceiling)}."
                )
    elif mentions_price_ceiling(normalized_question):
        parts.append("Eu ainda não tenho seu preço-teto salvo para comparar isso de forma confiável.")

    if in_watchlist:
        parts.append(f"{asset_name} já está na sua watchlist.")

    if thesis:
        parts.append(f"Sua tese salva para esse ativo hoje é: {thesis}")
    if any(term in normalized_question for term in {"barato", "caro"}):
        parts.append("Com esse recorte sozinho, eu ainda não chamaria de barato ou caro com convicção; precisaria cruzar preço, fundamento e seu critério.")
    else:
        parts.append("Minha leitura prática é que isso pede olhar conjunto para momento, tese e risco, não só para um número isolado.")

    if summary and len(summary) < 220:
        parts.append(f"O contexto salvo sugere isto: {summary}")

    return " ".join(parts)
