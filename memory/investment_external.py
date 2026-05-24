from collections.abc import Callable

from memory.investment_formatting import format_brl, parse_percent_value

GetStrategy = Callable[[str], dict]


def external_asset_opinion(
    ticker: str,
    fundamentals: dict,
    *,
    external_effective_price_ceiling: Callable[[str, dict], tuple[float | None, str]],
) -> tuple[str, str]:
    quote_value = fundamentals.get("quote_value")
    dy_percent = fundamentals.get("dividend_yield_current_percent")
    p_vp = parse_percent_value(fundamentals.get("p_vp")) if isinstance(fundamentals.get("p_vp"), str) else None
    try:
        if p_vp is None and fundamentals.get("p_vp") not in (None, ""):
            p_vp = float(str(fundamentals.get("p_vp")).replace(".", "").replace(",", "."))
    except Exception:
        p_vp = None
    try:
        p_l = float(str(fundamentals.get("p_l")).replace(".", "").replace(",", ".")) if fundamentals.get("p_l") not in (None, "") else None
    except Exception:
        p_l = None
    ceiling, source = external_effective_price_ceiling(ticker, fundamentals)

    if quote_value is not None and ceiling is not None and quote_value > ceiling and source == "manual":
        return (
            "Pelo seu critério de preço, ele ainda pede cautela.",
            "Hoje, eu trataria mais como ativo para observar do que para aportar.",
        )
    if quote_value is not None and ceiling is not None and quote_value <= ceiling:
        return (
            "Pelo seu critério de preço, ele parece mais aceitável para estudo de entrada.",
            "Hoje, eu trataria mais como oportunidade em estudo do que como compra automática.",
        )
    if dy_percent is not None and dy_percent >= 8 and p_vp is not None and p_vp <= 1.05:
        return (
            "Para renda, o conjunto de dividend yield e preço patrimonial parece interessante, embora eu ainda confirmasse a qualidade do ativo.",
            "Hoje, ele me parece mais um nome para aporte estudado do que para simples espera.",
        )
    if p_l is not None and p_l < 0:
        return (
            "Como o lucro ainda não sustenta bem a leitura, eu iria com mais prudência.",
            "Hoje, eu trataria mais como ativo para observar do que para aportar.",
        )
    return (
        "Eu cruzaria preço, qualidade e risco antes de chamar de oportunidade.",
        "Hoje, eu trataria mais como posição para observar e acompanhar.",
    )


def format_external_asset_reading(
    ticker: str,
    fundamentals: dict,
    *,
    get_asset_strategy: GetStrategy,
    external_effective_price_ceiling: Callable[[str, dict], tuple[float | None, str]],
    external_asset_opinion_fn: Callable[[str, dict], tuple[str, str]],
) -> str:
    strategy = get_asset_strategy(ticker)
    company_name = str(fundamentals.get("company_name") or "").strip()
    quote = str(fundamentals.get("quote") or "").strip()
    dy_current = str(fundamentals.get("dividend_yield_current") or "").strip()
    dy_average = str(fundamentals.get("dividend_yield_5y_average") or "").strip()
    p_vp = str(fundamentals.get("p_vp") or "").strip()
    p_l = str(fundamentals.get("p_l") or "").strip()
    ceiling, source = external_effective_price_ceiling(ticker, fundamentals)
    opinion, stance = external_asset_opinion_fn(ticker, fundamentals)

    label = ticker
    if company_name:
        label += f", {company_name}"

    parts = [f"Sobre {label}, a cotação atual está em {quote or 'valor não identificado'}."]
    if dy_current:
        if dy_average:
            parts.append(f"O dividend yield atual está em {dy_current}, com média de 5 anos em {dy_average}.")
        else:
            parts.append(f"O dividend yield atual está em {dy_current}.")
    if p_vp:
        parts.append(f"O P sobre VP está em {p_vp}.")
    if p_l:
        parts.append(f"O P sobre L está em {p_l}.")
    if ceiling is not None:
        if source == "manual":
            parts.append(f"Seu preço-teto salvo para {ticker} está em {format_brl(ceiling)}.")
        elif source == "automatic_yield":
            parts.append(f"Pela base automática por yield alvo, o preço-teto estimado ficaria em {format_brl(ceiling)}.")
        elif source == "automatic":
            parts.append(f"Pela base automática atual, o preço-teto estimado ficaria em {format_brl(ceiling)}.")
    thesis = str(strategy.get("thesis", "")).strip()
    if thesis:
        parts.append(f"Sua tese curta salva para esse ativo é: {thesis}")
    if strategy.get("in_watchlist"):
        parts.append(f"{ticker} já está na sua watchlist.")
    parts.append(opinion)
    parts.append(stance)
    return " ".join(parts)
