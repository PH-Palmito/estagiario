import time
from typing import Callable

from memory.investment_formatting import format_brl, parse_currency_value, parse_percent_value


GetStrategy = Callable[[str], dict]
LoadStrategy = Callable[[], dict]
AssetPositions = Callable[[dict], dict[str, dict]]
AssetFundamentals = Callable[[dict], dict[str, dict]]
SignalState = Callable[[], dict]
SaveSignalState = Callable[[dict], None]
CalculateAutoPriceCeiling = Callable[[float | None, float | None], float | None]


def _is_no(value: str) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"não", "nao"}


def resolve_reference_price(position: dict, strategy: dict) -> float | None:
    reference_name = str(strategy.get("auto_ceiling_reference", "preco_medio")).strip()
    if reference_name == "cotacao_atual":
        return parse_currency_value(position.get("current_price"))
    return parse_currency_value(position.get("average_price")) or parse_currency_value(position.get("current_price"))


def effective_price_ceiling(
    snapshot: dict,
    ticker: str,
    position: dict,
    *,
    get_asset_strategy: GetStrategy,
    asset_fundamentals: AssetFundamentals,
    calculate_auto_price_ceiling: CalculateAutoPriceCeiling,
) -> tuple[float | None, str]:
    strategy = get_asset_strategy(ticker)
    manual_ceiling = strategy.get("price_ceiling")
    if manual_ceiling is not None:
        return float(manual_ceiling), "manual"

    if not strategy.get("auto_ceiling_enabled"):
        return None, "none"

    if str(strategy.get("auto_ceiling_method", "")).strip() == "yield_alvo":
        fundamentals = asset_fundamentals(snapshot).get(ticker, {})
        annual_dividend = fundamentals.get("annual_dividend_estimate_per_share")
        target_yield = strategy.get("auto_ceiling_target_yield_percent")
        if annual_dividend and target_yield:
            try:
                ceiling = float(annual_dividend) / (float(target_yield) / 100.0)
                if ceiling > 0:
                    return ceiling, "automatic_yield"
            except Exception:
                pass

    reference_price = resolve_reference_price(position, strategy)
    auto_ceiling = calculate_auto_price_ceiling(reference_price, strategy.get("auto_ceiling_margin_percent"))
    if auto_ceiling is None:
        return None, "none"
    return float(auto_ceiling), "automatic"


def external_effective_price_ceiling(
    ticker: str,
    fundamentals: dict,
    *,
    get_asset_strategy: GetStrategy,
    calculate_auto_price_ceiling: CalculateAutoPriceCeiling,
) -> tuple[float | None, str]:
    strategy = get_asset_strategy(ticker)
    manual_ceiling = strategy.get("price_ceiling")
    if manual_ceiling is not None:
        return float(manual_ceiling), "manual"

    if not strategy.get("auto_ceiling_enabled"):
        return None, "none"

    annual_dividend = fundamentals.get("annual_dividend_estimate_per_share")
    target_yield = strategy.get("auto_ceiling_target_yield_percent")
    if annual_dividend and target_yield:
        try:
            ceiling = float(annual_dividend) / (float(target_yield) / 100.0)
            if ceiling > 0:
                return ceiling, "automatic_yield"
        except Exception:
            pass

    quote_value = fundamentals.get("quote_value")
    auto_ceiling = calculate_auto_price_ceiling(quote_value, strategy.get("auto_ceiling_margin_percent"))
    if auto_ceiling is None:
        return None, "none"
    return float(auto_ceiling), "automatic"


def portfolio_items_above_ceiling(
    snapshot: dict,
    *,
    asset_positions: AssetPositions,
    effective_price_ceiling_fn: Callable[[dict, str, dict], tuple[float | None, str]],
) -> list[dict]:
    results: list[dict] = []
    for ticker, position in asset_positions(snapshot).items():
        current_price = parse_currency_value(position.get("current_price"))
        ceiling, source = effective_price_ceiling_fn(snapshot, ticker, position)
        if source == "none" or current_price is None or ceiling is None or current_price <= ceiling:
            continue
        premium_percent = ((current_price / ceiling) - 1.0) * 100.0 if ceiling > 0 else None
        results.append(
            {
                "ticker": ticker,
                "current_price": current_price,
                "ceiling": ceiling,
                "source": source,
                "premium_percent": premium_percent,
            }
        )
    return sorted(results, key=lambda item: item.get("premium_percent") or 0.0, reverse=True)


def is_price_ceiling_alert_material(
    item: dict,
    *,
    signal_seen_state: SignalState,
    save_signal_seen_state: SaveSignalState,
    threshold_percent: float = 2.0,
) -> bool:
    ticker = str(item.get("ticker") or "").upper()
    if not ticker:
        return False

    current_price = item.get("current_price")
    ceiling = item.get("ceiling")
    premium_percent = item.get("premium_percent")
    state = signal_seen_state()
    previous_by_ticker = state.get("price_ceiling_by_ticker")
    if not isinstance(previous_by_ticker, dict):
        previous_by_ticker = {}

    previous = previous_by_ticker.get(ticker)
    material = True
    if isinstance(previous, dict):
        previous_premium = previous.get("premium_percent")
        previous_price = previous.get("current_price")
        material = False
        try:
            if previous_premium is None or premium_percent is None:
                material = previous_premium != premium_percent
            elif abs(float(premium_percent) - float(previous_premium)) >= threshold_percent:
                material = True
        except Exception:
            material = True
        try:
            if not material and previous_price and current_price:
                price_change = abs((float(current_price) / float(previous_price)) - 1.0) * 100.0
                material = price_change >= threshold_percent
        except Exception:
            pass

    previous_by_ticker[ticker] = {
        "current_price": current_price,
        "ceiling": ceiling,
        "premium_percent": premium_percent,
        "source": item.get("source"),
        "updated_at": time.time(),
    }
    state["price_ceiling_by_ticker"] = previous_by_ticker
    state["updated_at"] = time.time()
    save_signal_seen_state(state)
    return material


def material_price_ceiling_items(
    items: list[dict],
    *,
    is_alert_material: Callable[[dict], bool],
) -> list[dict]:
    return [item for item in items if is_alert_material(item)]


def watchlist_tickers_not_in_portfolio(
    snapshot: dict,
    *,
    load_investment_strategy: LoadStrategy,
    asset_positions: AssetPositions,
) -> list[str]:
    strategy = load_investment_strategy()
    watchlist = [str(item).upper() for item in strategy.get("watchlist", []) if str(item).strip()]
    portfolio = set(asset_positions(snapshot).keys())
    return [ticker for ticker in dict.fromkeys(watchlist) if ticker and ticker not in portfolio]


def portfolio_attention_items(
    snapshot: dict,
    *,
    asset_positions: AssetPositions,
    effective_price_ceiling_fn: Callable[[dict, str, dict], tuple[float | None, str]],
) -> list[dict]:
    items: list[dict] = []
    for ticker, position in asset_positions(snapshot).items():
        reasons: list[str] = []
        opinions: list[str] = []
        current_price = parse_currency_value(position.get("current_price"))
        average_price = parse_currency_value(position.get("average_price"))
        variation = parse_percent_value(position.get("variation"))
        rentability = parse_percent_value(position.get("rentability"))
        portfolio_percentage = parse_percent_value(position.get("portfolio_percentage"))
        ideal_percentage = parse_percent_value(position.get("ideal_percentage"))
        rating_text = str(position.get("rating", "")).strip()
        buy_more = str(position.get("buy_more", "")).strip().lower()

        ceiling, source = effective_price_ceiling_fn(snapshot, ticker, position)
        if source == "manual" and current_price is not None and ceiling is not None and current_price > ceiling:
            reasons.append("acima de seu preço-teto")
            opinions.append("isso pede mais cautela antes de aumentar posição")
        if rentability is not None and rentability <= -10:
            reasons.append(f"rentabilidade fraca em {position.get('rentability')}")
            opinions.append("vale revisar se a tese continua firme")
        if variation is not None and variation <= -10:
            reasons.append(f"queda recente de {position.get('variation')}")
        if portfolio_percentage is not None and ideal_percentage is not None and portfolio_percentage > (ideal_percentage + 0.75):
            reasons.append("peso acima do ideal")
            opinions.append("talvez valha evitar concentrar ainda mais")
        if rating_text.isdigit() and int(rating_text) <= 5:
            reasons.append(f"nota interna em {rating_text}")
        if average_price is not None and current_price is not None and current_price < average_price and _is_no(buy_more):
            reasons.append("abaixo do preço médio sem sinal de compra adicional")
            opinions.append("pode valer uma revisão de compra se a tese seguir intacta")

        if reasons:
            items.append(
                {
                    "ticker": ticker,
                    "reasons": reasons,
                    "opinions": opinions,
                    "current_price": position.get("current_price"),
                    "rentability": position.get("rentability"),
                }
            )
    return items


def position_quick_opinion(
    snapshot: dict,
    ticker: str,
    position: dict,
    *,
    effective_price_ceiling_fn: Callable[[dict, str, dict], tuple[float | None, str]],
) -> str:
    current_price = parse_currency_value(position.get("current_price"))
    average_price = parse_currency_value(position.get("average_price"))
    variation = parse_percent_value(position.get("variation"))
    rentability = parse_percent_value(position.get("rentability"))
    ceiling, source = effective_price_ceiling_fn(snapshot, ticker, position)

    if source == "manual" and current_price is not None and ceiling is not None and current_price > ceiling:
        return "Para o seu critério, eu iria com mais cautela antes de aumentar posição."

    if average_price is not None and current_price is not None and current_price < average_price:
        if str(position.get("buy_more", "")).strip().lower() == "sim":
            return "Como ele está abaixo do seu preço médio, pode fazer sentido estudar novo aporte se a tese seguir firme."
        return "Estar abaixo do preço médio pode abrir oportunidade, mas eu revisaria a tese antes de comprar mais."

    if rentability is not None and rentability <= -10:
        return "Aqui eu daria mais peso à revisão da tese do que ao impulso de comprar por queda."

    if variation is not None and variation <= -10:
        return "Queda forte assim pede calma; eu tentaria entender se é ruído ou mudança de fundamento."

    if current_price is not None and ceiling is not None and current_price <= ceiling:
        return "Pelo seu critério de preço, ele parece mais perto de uma zona aceitável de entrada."

    return "Eu olharia preço, tese e risco do setor juntos antes de decidir qualquer aporte."


def position_action_stance(
    snapshot: dict,
    ticker: str,
    position: dict,
    *,
    effective_price_ceiling_fn: Callable[[dict, str, dict], tuple[float | None, str]],
) -> str:
    current_price = parse_currency_value(position.get("current_price"))
    average_price = parse_currency_value(position.get("average_price"))
    variation = parse_percent_value(position.get("variation"))
    rentability = parse_percent_value(position.get("rentability"))
    ceiling, source = effective_price_ceiling_fn(snapshot, ticker, position)
    buy_more = str(position.get("buy_more", "")).strip().lower()

    if source == "manual" and current_price is not None and ceiling is not None and current_price > ceiling:
        return "Hoje, eu trataria mais como ativo para observar do que para aportar."
    if average_price is not None and current_price is not None and current_price < average_price:
        if buy_more == "sim":
            return "Hoje, ele me parece mais um nome para aporte estudado do que para simples espera."
        return "Hoje, eu trataria mais como oportunidade em estudo do que como compra automática."
    if rentability is not None and rentability <= -10:
        return "Hoje, eu inclinaria mais para segurar e revisar a tese do que para aumentar posição."
    if variation is not None and variation <= -10:
        return "Hoje, eu deixaria mais em observação até entender melhor o motivo da queda."
    if current_price is not None and ceiling is not None and current_price <= ceiling:
        return "Hoje, ele parece mais próximo de uma faixa aceitável para aporte."
    return "Hoje, eu trataria mais como posição para segurar e acompanhar."
