from collections.abc import Callable

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

    dividend_events = portfolio_dividend_schedule(snapshot, limit=1)
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
