from typing import Callable

from memory.investment_formatting import format_percent, parse_percent_value


RankPositions = Callable[[dict], list[tuple[str, dict]]]
EnsureFundamentals = Callable[[dict, str], dict]
IsProbableFii = Callable[[str, dict | None], bool]
CategoryBreakdown = Callable[[dict], dict[str, str]]
UnresolvedCounts = Callable[[dict], dict[str, dict]]


def portfolio_fii_dy_answer(
    snapshot: dict,
    *,
    rank_portfolio_positions: RankPositions,
    ensure_asset_fundamentals: EnsureFundamentals,
    is_probable_fii_ticker: IsProbableFii,
    category_breakdown: CategoryBreakdown,
    unresolved_category_counts: UnresolvedCounts,
) -> str:
    fii_rows: list[tuple[str, str, float]] = []
    weighted_sum = 0.0
    weight_total = 0.0

    for ticker, position in rank_portfolio_positions(snapshot):
        fundamentals = ensure_asset_fundamentals(snapshot, ticker)
        if not is_probable_fii_ticker(ticker, fundamentals):
            continue
        dy_label = str(fundamentals.get("dividend_yield_current") or "").strip()
        dy_percent = fundamentals.get("dividend_yield_current_percent")
        if not dy_label or dy_percent in (None, ""):
            continue
        weight = parse_percent_value(position.get("portfolio_percentage")) or 0.0
        fii_rows.append((ticker, dy_label, weight))
        weighted_sum += float(dy_percent) * weight
        weight_total += weight

    if fii_rows:
        listed = "; ".join(f"{ticker} em {dy}" for ticker, dy, _weight in fii_rows)
        if weight_total > 0:
            weighted_average = weighted_sum / weight_total
            return (
                f"O DY dos seus FIIs salvos hoje está assim: {listed}. "
                f"Pelo peso atual desse bloco, o DY médio ponderado fica perto de {format_percent(weighted_average, digits=2)}."
            )
        return f"O DY dos seus FIIs salvos hoje está assim: {listed}."

    breakdown = category_breakdown(snapshot)
    fii_share = str(breakdown.get("FIIs") or "").strip()
    if fii_share:
        unresolved = unresolved_category_counts(snapshot).get("FIIs", {})
        reported = int(unresolved.get("reported") or 0) if isinstance(unresolved, dict) else 0
        captured = int(unresolved.get("captured") or 0) if isinstance(unresolved, dict) else 0
        source_label = "carteira privada" if str(snapshot.get("source", "")).strip() == "investidor10_private_wallet" else "carteira pública"
        detail_parts = []
        if reported:
            detail_parts.append(f"a {source_label} reporta {reported} ativos nesse bloco")
        if captured:
            detail_parts.append(f"eu consegui individualizar {captured}")
        details = ""
        if detail_parts:
            details = " Hoje, " + ", ".join(detail_parts) + "."
        return (
            f"Hoje eu sei que FIIs representam {fii_share} da sua carteira, mas a {source_label} ainda expõe esse bloco de forma agregada.{details} "
            "Então eu ainda não consigo te dar o DY dos seus FIIs um por um com confiança. "
            "Se você me disser um ticker específico, como XPML11 ou VGIA11, eu já consigo analisar DY, preço e dividendos dele."
        )

    return "No snapshot atual, eu não consegui identificar FIIs individualizados na carteira."
