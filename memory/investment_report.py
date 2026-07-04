from collections.abc import Callable
from datetime import date, datetime

from memory.investment_dividends import filter_dividend_events_by_payment_window

FilterSignals = Callable[[str, list[str]], list[str]]


def _attention_text(items: list[dict], limit: int = 3, *, include_opinion: bool = True) -> list[str]:
    texts: list[str] = []
    for item in items[:limit]:
        reason_text = ", ".join(item.get("reasons", [])[:2 if include_opinion else 1])
        opinion_text = ""
        opinions = item.get("opinions") or []
        if include_opinion and opinions:
            opinion_text = str(opinions[0]).strip()
        if opinion_text:
            texts.append(f"{item['ticker']} ({reason_text}); minha leitura: {opinion_text}")
        else:
            texts.append(f"{item['ticker']}: {reason_text}" if not include_opinion else f"{item['ticker']} ({reason_text})")
    return texts


def _ceiling_text(items: list[dict], *, format_percent: Callable[..., str]) -> list[str]:
    texts: list[str] = []
    for item in items:
        premium = format_percent(item.get("premium_percent"), digits=1)
        texts.append(
            f"{item['ticker']} acima do teto em {premium}"
            if premium
            else f"{item['ticker']} acima do teto"
        )
    return texts


def _safe_float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _latest_history_pair(history_items: list[dict], current_date: str = "") -> tuple[dict | None, dict | None]:
    items = [item for item in history_items if isinstance(item, dict)]
    items.sort(key=lambda item: (str(item.get("date") or ""), float(item.get("updated_at") or 0)))
    if not items:
        return None, None

    current = items[-1]
    current_key = str(current_date or current.get("date") or "").strip()
    previous = None
    for item in reversed(items[:-1]):
        item_date = str(item.get("date") or "").strip()
        if current_key and item_date == current_key:
            continue
        previous = item
        break
    return current, previous


def _delta_text(label: str, current: float | None, previous: float | None, *, formatter: Callable[[float | None], str]) -> str:
    if current is None:
        return ""
    current_text = formatter(current)
    if previous is None:
        return f"{label} {current_text}"
    delta = current - previous
    direction = "subiu" if delta > 0 else "caiu" if delta < 0 else "ficou estavel"
    delta_text = formatter(abs(delta))
    if direction == "ficou estavel":
        return f"{label} {current_text}, estavel desde o ultimo snapshot"
    return f"{label} {current_text}, {direction} {delta_text} desde o ultimo snapshot"


def _rank_daily_asset_variations(
    snapshot: dict,
    *,
    parse_percent_value: Callable[[str], float | None],
    limit: int = 3,
) -> list[str]:
    positions = snapshot.get("asset_positions")
    if not isinstance(positions, dict):
        return []
    ranked: list[tuple[float, str, str]] = []
    for ticker, position in positions.items():
        if not isinstance(position, dict):
            continue
        variation = str(position.get("variation") or "").strip()
        value = parse_percent_value(variation)
        if value is None:
            continue
        ranked.append((abs(value), str(ticker).upper(), variation))
    ranked.sort(reverse=True)
    return [f"{ticker} {variation}" for _, ticker, variation in ranked[:limit]]


def investment_daily_change_report(
    snapshot: dict,
    history_items: list[dict],
    *,
    portfolio_items_above_ceiling: Callable[[dict], list[dict]],
    portfolio_dividend_schedule: Callable[..., list[dict]],
    format_dividend_event_brief: Callable[[str, dict], str],
    portfolio_news_digest: Callable[..., list[str]],
    parse_percent_value: Callable[[str], float | None],
    format_brl: Callable[[float | None], str],
    format_percent: Callable[..., str],
) -> str:
    updated_at = float(snapshot.get("updated_at") or 0)
    summary = str(snapshot.get("summary") or "").strip()
    if not updated_at and not summary and not history_items:
        return "Ainda nao tenho historico da carteira para comparar com ontem. Atualize a carteira primeiro."

    current_date = ""
    if updated_at:
        import time

        current_date = time.strftime("%Y-%m-%d", time.localtime(updated_at))
    current, previous = _latest_history_pair(history_items, current_date=current_date)

    parts: list[str] = []
    if current and previous:
        parts.append(f"Comparando {current.get('date')} com {previous.get('date')}.")
    elif current:
        parts.append(f"Tenho apenas o snapshot de {current.get('date')}; ainda nao ha dia anterior salvo para comparar.")
    else:
        parts.append("Tenho a carteira atual, mas o historico diario ainda nao foi formado.")

    metrics: list[str] = []
    if current:
        metrics.append(
            _delta_text(
                "Patrimonio",
                _safe_float(current.get("patrimonio_value")),
                _safe_float((previous or {}).get("patrimonio_value")),
                formatter=format_brl,
            )
        )
        metrics.append(
            _delta_text(
                "Rentabilidade",
                _safe_float(current.get("rentabilidade_percent")),
                _safe_float((previous or {}).get("rentabilidade_percent")),
                formatter=lambda value: format_percent(value, digits=2),
            )
        )
        metrics.append(
            _delta_text(
                "Cripto",
                _safe_float(current.get("crypto_balance_value")),
                _safe_float((previous or {}).get("crypto_balance_value")),
                formatter=format_brl,
            )
        )
    metrics = [item for item in metrics if item]
    if metrics:
        parts.append("Mudancas principais: " + "; ".join(metrics) + ".")

    asset_variations = _rank_daily_asset_variations(snapshot, parse_percent_value=parse_percent_value)
    if asset_variations:
        parts.append("Ativos com maior variacao visivel no snapshot atual: " + "; ".join(asset_variations) + ".")

    dividend_events = portfolio_dividend_schedule(snapshot, limit=2)
    if dividend_events:
        dividend_text = [format_dividend_event_brief(item["ticker"], item["event"]) for item in dividend_events[:2]]
        parts.append("Dividendos no radar: " + "; ".join(dividend_text) + ".")

    ceiling_items = portfolio_items_above_ceiling(snapshot)[:2]
    if ceiling_items:
        ceiling_text = _ceiling_text(ceiling_items, format_percent=format_percent)
        if ceiling_text:
            parts.append("Preco-teto: " + "; ".join(ceiling_text) + ".")

    news_items = portfolio_news_digest(snapshot, limit_assets=4, limit_summaries=1, only_new=False, mark_seen=False)
    if news_items:
        parts.append("Noticia relevante: " + news_items[0].strip(".") + ".")

    return "Resumo diario da carteira. " + " ".join(part for part in parts if part)


def portfolio_monitor_digest(
    snapshot: dict,
    *,
    portfolio_attention_items: Callable[[dict], list[dict]],
    portfolio_items_above_ceiling: Callable[[dict], list[dict]],
    material_price_ceiling_items: Callable[[list[dict]], list[dict]],
    vacancy_alert_items: Callable[[dict], list[str]],
    volatility_alert_items: Callable[[dict], list[str]],
    portfolio_dividend_schedule: Callable[..., list[dict]],
    format_dividend_event: Callable[[str, dict], str],
    portfolio_news_digest: Callable[..., list[str]],
    filter_new_signal_texts: Callable[..., list[str]],
    format_percent: Callable[..., str],
) -> str:
    parts: list[str] = []

    attention_items = portfolio_attention_items(snapshot)[:3]
    attention_text = _attention_text(attention_items, limit=3, include_opinion=True) if attention_items else []
    attention_text = filter_new_signal_texts("attention", attention_text, only_new=True, mark_seen=True)[:3]
    if attention_text:
        parts.append("Pontos de atenção: " + "; ".join(attention_text) + ".")

    ceiling_items = material_price_ceiling_items(portfolio_items_above_ceiling(snapshot))[:2]
    ceiling_text = _ceiling_text(ceiling_items, format_percent=format_percent) if ceiling_items else []
    if ceiling_text:
        parts.append("Preço-teto com mudança relevante: " + "; ".join(ceiling_text) + ".")

    vacancy_items = filter_new_signal_texts("vacancy", vacancy_alert_items(snapshot), only_new=True, mark_seen=True)[:2]
    if vacancy_items:
        parts.append("Vacância no radar: " + "; ".join(vacancy_items) + ".")

    volatility_items = filter_new_signal_texts("volatility", volatility_alert_items(snapshot), only_new=True, mark_seen=True)[:2]
    if volatility_items:
        parts.append("Volatilidade no radar: " + "; ".join(volatility_items) + ".")

    dividend_events = portfolio_dividend_schedule(snapshot, limit=2)
    if dividend_events:
        dividend_items = [format_dividend_event(item["ticker"], item["event"]) for item in dividend_events]
        dividend_items = filter_new_signal_texts("dividend", dividend_items, only_new=True, mark_seen=True)[:2]
        if dividend_items:
            parts.append("Próximos dividendos identificados: " + "; ".join(dividend_items) + ".")

    news_items = portfolio_news_digest(snapshot, limit_assets=4, limit_summaries=1, only_new=True, mark_seen=True)
    if news_items:
        parts.append("Notícia que merece radar: " + news_items[0] + ".")

    if parts:
        return "Monitoramento atual da carteira: " + " ".join(parts)
    return "No momento, eu não encontrei sinal forte de monitoramento além do resumo normal da carteira."


def investment_financial_report(
    snapshot: dict,
    *,
    category_breakdown: Callable[[dict], dict],
    portfolio_attention_items: Callable[[dict], list[dict]],
    portfolio_items_above_ceiling: Callable[[dict], list[dict]],
    material_price_ceiling_items: Callable[[list[dict]], list[dict]],
    vacancy_alert_items: Callable[[dict], list[str]],
    volatility_alert_items: Callable[[dict], list[str]],
    portfolio_dividend_schedule: Callable[..., list[dict]],
    format_dividend_event_brief: Callable[[str, dict], str],
    portfolio_news_digest: Callable[..., list[str]],
    compact_report_news: Callable[[str], str],
    filter_new_signal_texts: Callable[..., list[str]],
    format_percent: Callable[..., str],
    max_days_until_dividend: int | None = None,
    today: date | None = None,
) -> str:
    updated_at = float(snapshot.get("updated_at") or 0)
    metric_map = snapshot.get("metric_map") or {}

    if not updated_at and not snapshot.get("summary"):
        return "Ainda não tenho dados suficientes para montar um relatório financeiro. Atualize a carteira primeiro."

    report_parts: list[str] = []

    patrimonio = str(metric_map.get("patrimonio") or "").strip()
    rentabilidade = str(metric_map.get("rentabilidade") or "").strip()
    proventos = str(metric_map.get("proventos") or "").strip()
    summary_bits = []
    if patrimonio:
        summary_bits.append(f"patrimônio {patrimonio}")
    if rentabilidade:
        summary_bits.append(f"rentabilidade {rentabilidade}")
    if proventos:
        summary_bits.append(f"proventos {proventos}")
    if summary_bits:
        report_parts.append("Resumo: " + "; ".join(summary_bits) + ".")
    else:
        summary = str(snapshot.get("summary") or "").strip()
        if summary:
            report_parts.append("Resumo: " + summary.strip(".") + ".")

    breakdown = category_breakdown(snapshot)
    if breakdown:
        allocation = "; ".join(f"{category} {value}" for category, value in list(breakdown.items())[:3] if value)
        if allocation:
            report_parts.append("Alocação atual: " + allocation + ".")

    attention_items = portfolio_attention_items(snapshot)[:2]
    attention_parts = _attention_text(attention_items, limit=2, include_opinion=False) if attention_items else []
    attention_parts = filter_new_signal_texts("attention", attention_parts, only_new=True, mark_seen=True)[:2]
    if attention_parts:
        report_parts.append("Atenção: " + "; ".join(attention_parts) + ".")

    ceiling_items = material_price_ceiling_items(portfolio_items_above_ceiling(snapshot))[:2]
    ceiling_parts = _ceiling_text(ceiling_items, format_percent=format_percent) if ceiling_items else []
    if ceiling_parts:
        report_parts.append("Preço-teto: " + "; ".join(ceiling_parts) + ".")

    vacancy_parts = filter_new_signal_texts("vacancy", vacancy_alert_items(snapshot), only_new=True, mark_seen=True)[:2]
    if vacancy_parts:
        report_parts.append("Vacância: " + "; ".join(vacancy_parts) + ".")

    volatility_parts = filter_new_signal_texts("volatility", volatility_alert_items(snapshot), only_new=True, mark_seen=True)[:2]
    if volatility_parts:
        report_parts.append("Volatilidade: " + "; ".join(volatility_parts) + ".")

    dividend_limit = 5 if max_days_until_dividend is not None else 1
    dividend_events = portfolio_dividend_schedule(snapshot, limit=dividend_limit)
    dividend_events = filter_dividend_events_by_payment_window(
        dividend_events,
        max_days_until_payment=max_days_until_dividend,
        today=today or datetime.now().date(),
    )
    if dividend_events:
        dividend_parts = [format_dividend_event_brief(item["ticker"], item["event"]) for item in dividend_events]
        dividend_parts = filter_new_signal_texts("dividend", dividend_parts, only_new=True, mark_seen=True)
        if dividend_parts:
            report_parts.append("Próximo dividendo no radar: " + "; ".join(dividend_parts[:1]) + ".")

    news_items = portfolio_news_digest(snapshot, limit_assets=5, limit_summaries=1, only_new=True, mark_seen=True)
    if news_items:
        compact_news = compact_report_news(news_items[0])
        if compact_news:
            report_parts.append("Notícia nova relevante: " + compact_news)

    if attention_parts or ceiling_parts or vacancy_parts or volatility_parts:
        report_parts.append("Leitura geral: revisar antes de aumentar posição.")
    else:
        report_parts.append("Leitura geral: sem alerta crítico novo salvo agora.")

    return "Relatório financeiro. " + " ".join(part for part in report_parts if part)


def investment_active_radar_brief(
    snapshot: dict,
    *,
    portfolio_attention_items: Callable[[dict], list[dict]],
    portfolio_items_above_ceiling: Callable[[dict], list[dict]],
    material_price_ceiling_items: Callable[[list[dict]], list[dict]],
    volatility_alert_items: Callable[[dict], list[str]],
    portfolio_dividend_schedule: Callable[..., list[dict]],
    format_dividend_event_brief: Callable[[str, dict], str],
    portfolio_news_digest: Callable[..., list[str]],
    compact_report_news: Callable[[str], str],
    format_percent: Callable[..., str],
    max_days_until_dividend: int | None = None,
    today: date | None = None,
) -> str:
    updated_at = float(snapshot.get("updated_at") or 0)
    if not updated_at and not snapshot.get("summary"):
        return "Radar da carteira: atualize a carteira para eu cruzar alertas financeiros."

    signals: list[str] = []

    attention_items = portfolio_attention_items(snapshot)[:2]
    attention_parts = _attention_text(attention_items, limit=2, include_opinion=False) if attention_items else []
    attention_tickers = [str(item).split(":", 1)[0].strip() for item in attention_parts if str(item).strip()]
    if attention_tickers:
        signals.append("atenção em " + ", ".join(dict.fromkeys(attention_tickers[:2])))

    ceiling_items = portfolio_items_above_ceiling(snapshot)[:2]
    ceiling_parts = _ceiling_text(ceiling_items, format_percent=format_percent) if ceiling_items else []
    ceiling_tickers = [str(item).split(" ", 1)[0].strip() for item in ceiling_parts if str(item).strip()]
    if ceiling_tickers:
        signals.append("acima do teto: " + ", ".join(dict.fromkeys(ceiling_tickers[:2])))

    volatility_parts = volatility_alert_items(snapshot)[:2]
    if volatility_parts:
        signals.append("volatilidade: " + ", ".join(str(item).strip() for item in volatility_parts if str(item).strip()))

    dividend_limit = 5 if max_days_until_dividend is not None else 1
    dividend_events = portfolio_dividend_schedule(snapshot, limit=dividend_limit)
    dividend_events = filter_dividend_events_by_payment_window(
        dividend_events,
        max_days_until_payment=max_days_until_dividend,
        today=today or datetime.now().date(),
    )
    if dividend_events:
        dividend_parts = [format_dividend_event_brief(item["ticker"], item["event"]) for item in dividend_events]
        if dividend_parts:
            signals.append(str(dividend_parts[0]).strip("."))

    news_items = portfolio_news_digest(snapshot, limit_assets=5, limit_summaries=1, only_new=False, mark_seen=False)
    if news_items:
        compact_news = compact_report_news(news_items[0])
        if compact_news:
            signals.append("notícia relevante: " + compact_news.strip("."))

    if signals:
        return "Radar da carteira: alertas ativos: " + "; ".join(signals[:4]) + "."
    return "Radar da carteira: sem alerta ativo relevante agora."
