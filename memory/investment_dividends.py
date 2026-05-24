from collections.abc import Callable
from datetime import datetime

from memory.investment_formatting import (
    format_brl,
    format_day_month,
    parse_currency_value,
    parse_iso_datetime,
    parse_percent_value,
)

EnsureFundamentals = Callable[[dict, str], dict]
RankPositions = Callable[[dict], list[tuple[str, dict]]]
UnresolvedCounts = Callable[[dict], dict[str, dict]]


def ticker_dividend_events(snapshot: dict, ticker: str, ensure_asset_fundamentals: EnsureFundamentals) -> list[dict]:
    fundamentals = ensure_asset_fundamentals(snapshot, ticker)
    events = fundamentals.get("next_dividend_events")
    if not isinstance(events, list):
        return []
    ranked_events: list[tuple[datetime, dict]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        payment_date = parse_iso_datetime(event.get("payment_date"))
        last_date_prior = parse_iso_datetime(event.get("last_date_prior"))
        sort_key = payment_date or last_date_prior
        if not sort_key:
            continue
        ranked_events.append((sort_key, event))
    ranked_events.sort(key=lambda item: item[0])
    return [event for _, event in ranked_events]


def format_dividend_event(ticker: str, event: dict) -> str:
    details: list[str] = []
    rate_value = parse_currency_value(event.get("rate"))
    if rate_value is not None and rate_value > 1000:
        rate_value = rate_value / 1_000_000
    if rate_value is not None:
        details.append(f"valor de {format_brl(rate_value)} por cota")
    payment_day = format_day_month(event.get("payment_date"))
    if payment_day:
        details.append(f"pagamento em {payment_day}")
    last_date = format_day_month(event.get("last_date_prior"))
    if last_date:
        details.append(f"data-com até {last_date}")
    label = str(event.get("label") or "").strip()
    prefix = f"{ticker}"
    if label:
        prefix += f" ({label})"
    if details:
        return prefix + ": " + ", ".join(details)
    return prefix


def format_dividend_event_brief(ticker: str, event: dict) -> str:
    label = str(event.get("label") or "").strip()
    payment_day = format_day_month(event.get("payment_date"))
    if label and payment_day:
        return f"{ticker} paga {label} em {payment_day}"
    if payment_day:
        return f"{ticker} paga em {payment_day}"
    if label:
        return f"{ticker} tem {label} no radar"
    return ticker


def portfolio_dividend_schedule(
    snapshot: dict,
    *,
    rank_portfolio_positions: RankPositions,
    ensure_asset_fundamentals: EnsureFundamentals,
    limit: int = 5,
) -> list[dict]:
    events: list[dict] = []
    for ticker, position in rank_portfolio_positions(snapshot):
        ticker_events = ticker_dividend_events(snapshot, ticker, ensure_asset_fundamentals)
        if not ticker_events:
            continue
        for event in ticker_events[:2]:
            sort_key = parse_iso_datetime(event.get("payment_date")) or parse_iso_datetime(event.get("last_date_prior"))
            if not sort_key:
                continue
            events.append(
                {
                    "ticker": ticker,
                    "event": event,
                    "sort_key": sort_key,
                    "portfolio_percentage": parse_percent_value(position.get("portfolio_percentage")) or 0.0,
                }
            )
    events.sort(key=lambda item: (item["sort_key"], -item["portfolio_percentage"]))
    return events[: max(1, limit)]


def portfolio_dividend_schedule_answer(
    snapshot: dict,
    *,
    rank_portfolio_positions: RankPositions,
    ensure_asset_fundamentals: EnsureFundamentals,
    unresolved_category_counts: UnresolvedCounts,
) -> str:
    events = portfolio_dividend_schedule(
        snapshot,
        rank_portfolio_positions=rank_portfolio_positions,
        ensure_asset_fundamentals=ensure_asset_fundamentals,
        limit=5,
    )
    if events:
        details = "; ".join(format_dividend_event(item["ticker"], item["event"]) for item in events)
        return "Agenda de dividendos da carteira: " + details + "."

    unresolved = unresolved_category_counts(snapshot)
    fii_gap = unresolved.get("FIIs", {}) if isinstance(unresolved, dict) else {}
    fii_reported = int(fii_gap.get("reported") or 0) if isinstance(fii_gap, dict) else 0
    fii_captured = int(fii_gap.get("captured") or 0) if isinstance(fii_gap, dict) else 0
    other_missing = []
    for category, data in unresolved.items():
        if category == "FIIs" or not isinstance(data, dict):
            continue
        reported = int(data.get("reported") or 0)
        captured = int(data.get("captured") or 0)
        if reported > captured:
            other_missing.append(f"{category}: {captured} de {reported}")

    if fii_reported > fii_captured:
        parts = [
            "Ainda não encontrei uma agenda de dividendos confiável para a carteira inteira."
        ]
        parts.append(
            f"Hoje a fonte pública reporta {fii_reported} FIIs nesse bloco, mas eu só consegui individualizar {fii_captured} deles na memória da carteira."
        )
        if other_missing:
            parts.append("Também existem blocos ainda agregados em " + "; ".join(other_missing) + ".")
        parts.append(
            "Então os próximos proventos podem estar incompletos aqui. Se você me disser um ticker específico, como XPML11 ou VGIA11, eu já consigo checar DY e próximos dividendos dele."
        )
        return " ".join(parts)

    return "Ainda não encontrei uma agenda de dividendos confiável para a carteira inteira."


def upcoming_dividend_brief(
    snapshot: dict,
    *,
    rank_portfolio_positions: RankPositions,
    ensure_asset_fundamentals: EnsureFundamentals,
    limit: int = 2,
) -> str:
    events = portfolio_dividend_schedule(
        snapshot,
        rank_portfolio_positions=rank_portfolio_positions,
        ensure_asset_fundamentals=ensure_asset_fundamentals,
        limit=max(1, int(limit)),
    )
    if not events:
        return ""

    details = [
        format_dividend_event_brief(item["ticker"], item["event"])
        for item in events
    ]
    details = [item for item in details if item]
    if not details:
        return ""
    return "Dividendos próximos: " + "; ".join(details) + "."
