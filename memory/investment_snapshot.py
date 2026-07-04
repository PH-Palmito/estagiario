import re
import time
import unicodedata
from datetime import datetime
from pathlib import Path

from config import GEMINI_API_KEY
from llm.gemini_client import ask_gemini_grounded_model
from memory.investment_asset_fundamentals import fetch_asset_fundamentals
from memory.investment_base_answers import (
    answer_attention_assets,
    answer_auto_ceiling_settings,
    answer_empty_snapshot,
    answer_manual_assets_above_ceiling,
    answer_manual_price_ceiling,
    answer_metric_question,
    answer_missing_ticker_in_portfolio,
    answer_negative_assets,
    answer_price_criterion,
    answer_snapshot_updated_at,
    answer_thesis_status,
    answer_watchlist_status,
)
from memory.investment_decision import (
    effective_price_ceiling,
    external_effective_price_ceiling,
    is_price_ceiling_alert_material,
    material_price_ceiling_items,
    portfolio_attention_items,
    portfolio_items_above_ceiling,
    position_action_stance,
    position_quick_opinion,
    resolve_reference_price,
    watchlist_tickers_not_in_portfolio,
)
from memory.investment_dedup import (
    filter_new_signal_texts,
    load_seen_state,
    save_seen_state,
    signal_fingerprint,
    text_fingerprint,
)
from memory.investment_dividends import (
    format_dividend_event,
    format_dividend_event_brief,
    portfolio_dividend_schedule,
    portfolio_dividend_schedule_answer,
    ticker_dividend_events,
    upcoming_dividend_brief,
)
from memory.investment_external import (
    external_asset_opinion,
    format_external_asset_reading,
)
from memory.investment_fiis import portfolio_fii_dy_answer
from memory.investment_formatting import (
    format_brl,
    format_day_month,
    format_percent,
    parse_currency_value,
    parse_iso_datetime,
    parse_percent_value,
)
from memory.investment_grounded import (
    ask_grounded_asset_news,
    ask_grounded_investment_reading,
    asset_news_answer,
)
from memory.investment_news import (
    clean_news_lead,
    compact_report_news,
    portfolio_news_digest,
)
from memory.investment_parsing import (
    extract_metric_map,
    extract_question_ticker,
    extract_snapshot_direction,
    extract_ticker,
    snapshot_blob,
)
from memory.investment_question_answers import (
    answer_assets_above_ceiling,
    answer_auto_price_ceiling,
    answer_dividend_question,
    answer_portfolio_news_question,
    answer_ticker_average_price,
    answer_ticker_day_variation,
    answer_ticker_quote,
    answer_ticker_trend,
    answer_ticker_yield,
)
from memory.investment_reading import (
    build_local_investment_reading,
    format_position_reading,
)
from memory.investment_report import (
    investment_daily_change_report,
    investment_active_radar_brief,
    investment_financial_report,
    portfolio_monitor_digest,
)
from memory.investment_snapshot_store import (
    load_investment_snapshot_payload,
    load_json,
    save_investment_snapshot_payload,
    save_json,
)
from memory.investment_strategy import (
    calculate_auto_price_ceiling,
    get_asset_strategy,
    get_auto_ceiling_settings,
    load_investment_strategy,
)
from memory.news_api import summarize_asset_news
from memory.obsidian_sync import sync_portfolio_snapshot_note

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
INVESTMENT_SNAPSHOT_PATH = MEMORY_DIR / "investment_snapshot.json"
INVESTMENT_NEWS_SEEN_PATH = MEMORY_DIR / "investment_news_seen.json"
INVESTMENT_SIGNAL_SEEN_PATH = MEMORY_DIR / "investment_signal_seen.json"

def _save_json(path: Path, payload: dict):
    return save_json(path, payload)


def _load_json(path: Path):
    return load_json(path)


def _news_seen_state() -> dict:
    return load_seen_state(INVESTMENT_NEWS_SEEN_PATH, load_json=_load_json)


def _save_news_seen_state(state: dict) -> None:
    save_seen_state(INVESTMENT_NEWS_SEEN_PATH, state, save_json=_save_json)


def _signal_seen_state() -> dict:
    return load_seen_state(INVESTMENT_SIGNAL_SEEN_PATH, load_json=_load_json)


def _save_signal_seen_state(state: dict) -> None:
    save_seen_state(INVESTMENT_SIGNAL_SEEN_PATH, state, save_json=_save_json)


def _news_fingerprint(text: str) -> str:
    return text_fingerprint(text, normalize=_normalize)


def _signal_fingerprint(kind: str, text: str) -> str:
    return signal_fingerprint(kind, text, normalize=_normalize)


def _filter_new_signal_texts(kind: str, texts: list[str], *, only_new: bool = False, mark_seen: bool = False) -> list[str]:
    return filter_new_signal_texts(
        kind,
        texts,
        signal_state_path=INVESTMENT_SIGNAL_SEEN_PATH,
        load_json=_load_json,
        save_json=_save_json,
        normalize=_normalize,
        only_new=only_new,
        mark_seen=mark_seen,
    )


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or "").strip().lower())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    normalized = re.sub(r"[^\w\s%$.,:-]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def _format_timestamp(timestamp: float) -> str:
    if not timestamp:
        return "data desconhecida"
    return time.strftime("%d/%m/%Y às %H:%M", time.localtime(timestamp))


def _number_to_ptbr(value: int) -> str:
    units = {
        0: "zero",
        1: "um",
        2: "dois",
        3: "três",
        4: "quatro",
        5: "cinco",
        6: "seis",
        7: "sete",
        8: "oito",
        9: "nove",
        10: "dez",
        11: "onze",
        12: "doze",
        13: "treze",
        14: "quatorze",
        15: "quinze",
        16: "dezesseis",
        17: "dezessete",
        18: "dezoito",
        19: "dezenove",
        20: "vinte",
        30: "trinta",
        40: "quarenta",
        50: "cinquenta",
    }
    if value in units:
        return units[value]
    if 20 < value < 60:
        base = (value // 10) * 10
        remainder = value % 10
        return f"{units[base]} e {units[remainder]}"
    return str(value)


def _format_timestamp_natural(timestamp: float) -> str:
    if not timestamp:
        return "em data não identificada"
    months = (
        "janeiro",
        "fevereiro",
        "março",
        "abril",
        "maio",
        "junho",
        "julho",
        "agosto",
        "setembro",
        "outubro",
        "novembro",
        "dezembro",
    )
    struct = time.localtime(timestamp)
    day = _number_to_ptbr(struct.tm_mday)
    month = months[max(0, min(11, struct.tm_mon - 1))]
    hour = _number_to_ptbr(struct.tm_hour)
    minute = struct.tm_min
    if minute == 0:
        return f"em {day} de {month}, às {hour} horas"
    return f"em {day} de {month}, às {hour} horas e {_number_to_ptbr(minute)} minutos"


def _format_brl(value: float | None) -> str:
    return format_brl(value)


def _format_percent(value: float | None, digits: int = 1) -> str:
    return format_percent(value, digits=digits)


def _snapshot_blob(snapshot: dict) -> str:
    return snapshot_blob(snapshot)


def _extract_metric_map(metrics: list[str] | None, lines: list[str] | None) -> dict[str, str]:
    return extract_metric_map(metrics, lines, normalize=_normalize)


def _extract_ticker(snapshot: dict) -> str:
    return extract_ticker(snapshot)


def _extract_question_ticker(question: str) -> str:
    return extract_question_ticker(question)


def _mentions_price_ceiling(normalized: str) -> bool:
    compact = normalized.replace(" ", "")
    return "teto" in normalized and ("preco" in compact or "pre o" in normalized or "preco teto" in normalized)


def _contains_investment_phrase(normalized: str, *patterns: str) -> bool:
    text = str(normalized or "")
    compact = text.replace(" ", "")
    for pattern in patterns:
        raw = str(pattern or "").strip().lower()
        if not raw:
            continue
        raw_compact = raw.replace(" ", "")
        if raw in text or raw_compact in compact:
            return True
    return False


def _extract_snapshot_direction(snapshot: dict) -> str:
    return extract_snapshot_direction(snapshot, normalize=_normalize)


def _parse_currency_value(text: str) -> float | None:
    return parse_currency_value(text)


def _parse_percent_value(text: str) -> float | None:
    return parse_percent_value(text)


def _extract_current_price(snapshot: dict) -> float | None:
    metric_map = snapshot.get("metric_map") or {}
    direct = _parse_currency_value(metric_map.get("cotacao"))
    if direct is not None:
        return direct

    blob_lines = [str(item) for item in (snapshot.get("metrics") or [])] + [str(item) for item in (snapshot.get("lines") or [])]
    for line in blob_lines:
        if "cot" not in _normalize(line):
            continue
        match = re.search(r"r\$\s*([-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2}))", line, flags=re.I)
        if match:
            return _parse_currency_value(match.group(1))
    return None


def _asset_positions(snapshot: dict) -> dict[str, dict]:
    positions = snapshot.get("asset_positions")
    return positions if isinstance(positions, dict) else {}


def _asset_fundamentals(snapshot: dict) -> dict[str, dict]:
    fundamentals = snapshot.get("asset_fundamentals")
    if not isinstance(fundamentals, dict):
        return {}

    for ticker, data in list(fundamentals.items()):
        if not isinstance(data, dict):
            continue
        company_name = str(data.get("company_name") or "").strip()
        company_name_price = _parse_currency_value(company_name)
        if company_name_price is None:
            continue

        dy_percent = data.get("dividend_yield_current_percent")
        if dy_percent is None:
            dy_percent = _parse_percent_value(data.get("dividend_yield_current"))

        # Some Investidor10 pages expose the quote right after the ticker; the loose parser
        # can mistake that value for the company name and pick another currency as quote.
        data["quote"] = _format_brl(company_name_price)
        data["quote_value"] = company_name_price
        data["company_name"] = ""
        if dy_percent is not None:
            data["annual_dividend_estimate_per_share"] = company_name_price * (float(dy_percent) / 100.0)
        fundamentals[str(ticker).upper()] = data
    return fundamentals


def _category_breakdown(snapshot: dict) -> dict[str, str]:
    breakdown = snapshot.get("category_breakdown")
    return breakdown if isinstance(breakdown, dict) else {}


def _unresolved_category_counts(snapshot: dict) -> dict[str, dict]:
    unresolved = snapshot.get("unresolved_category_counts")
    return unresolved if isinstance(unresolved, dict) else {}


def _ensure_asset_fundamentals(snapshot: dict, ticker: str) -> dict:
    ticker = str(ticker or "").upper().strip()
    if not ticker:
        return {}
    fundamentals_map = _asset_fundamentals(snapshot)
    fundamentals = fundamentals_map.get(ticker, {})
    if fundamentals:
        return fundamentals
    try:
        fundamentals = fetch_asset_fundamentals(ticker) or {}
    except Exception:
        fundamentals = {}
    if fundamentals:
        fundamentals_map[ticker] = fundamentals
        snapshot["asset_fundamentals"] = fundamentals_map
    return fundamentals


def _parse_iso_datetime(value: str) -> datetime | None:
    return parse_iso_datetime(value)


def _format_day_month(value: str) -> str:
    return format_day_month(value)


def _rank_portfolio_positions(snapshot: dict) -> list[tuple[str, dict]]:
    ranked: list[tuple[str, dict, float, float]] = []
    for ticker, position in _asset_positions(snapshot).items():
        portfolio_weight = _parse_percent_value(position.get("portfolio_percentage")) or 0.0
        balance = _parse_currency_value(position.get("balance")) or 0.0
        ranked.append((ticker, position, portfolio_weight, balance))
    ranked.sort(key=lambda item: (item[2], item[3]), reverse=True)
    return [(ticker, position) for ticker, position, _, _ in ranked]


def _is_probable_fii_ticker(ticker: str, fundamentals: dict | None = None) -> bool:
    code = str(ticker or "").upper().strip()
    if code.endswith("11"):
        return True
    company_name = str((fundamentals or {}).get("company_name") or "").lower()
    return "fundo" in company_name or "fii" in company_name


def _resolve_reference_price(position: dict, strategy: dict) -> float | None:
    return resolve_reference_price(position, strategy)


def _effective_price_ceiling(snapshot: dict, ticker: str, position: dict) -> tuple[float | None, str]:
    return effective_price_ceiling(
        snapshot,
        ticker,
        position,
        get_asset_strategy=get_asset_strategy,
        asset_fundamentals=_asset_fundamentals,
        calculate_auto_price_ceiling=calculate_auto_price_ceiling,
    )


def _external_effective_price_ceiling(ticker: str, fundamentals: dict) -> tuple[float | None, str]:
    return external_effective_price_ceiling(
        ticker,
        fundamentals,
        get_asset_strategy=get_asset_strategy,
        calculate_auto_price_ceiling=calculate_auto_price_ceiling,
    )


def _portfolio_items_above_ceiling(snapshot: dict) -> list[dict]:
    return portfolio_items_above_ceiling(
        snapshot,
        asset_positions=_asset_positions,
        effective_price_ceiling_fn=_effective_price_ceiling,
    )


def _is_price_ceiling_alert_material(item: dict, *, threshold_percent: float = 2.0) -> bool:
    return is_price_ceiling_alert_material(
        item,
        signal_seen_state=_signal_seen_state,
        save_signal_seen_state=_save_signal_seen_state,
        threshold_percent=threshold_percent,
    )


def _material_price_ceiling_items(items: list[dict], *, threshold_percent: float = 2.0) -> list[dict]:
    return material_price_ceiling_items(
        items,
        is_alert_material=lambda item: _is_price_ceiling_alert_material(
            item,
            threshold_percent=threshold_percent,
        ),
    )


def _watchlist_tickers_not_in_portfolio(snapshot: dict) -> list[str]:
    return watchlist_tickers_not_in_portfolio(
        snapshot,
        load_investment_strategy=load_investment_strategy,
        asset_positions=_asset_positions,
    )


def _investment_news_candidates(snapshot: dict, limit_assets: int) -> list[tuple[str, str, dict]]:
    candidates: list[tuple[str, str, dict]] = []
    for ticker, position in _rank_portfolio_positions(snapshot):
        candidates.append((ticker, "carteira", position))
    for ticker in _watchlist_tickers_not_in_portfolio(snapshot):
        candidates.append((ticker, "watchlist", {}))
    return candidates[: max(1, limit_assets)]


def _vacancy_alert_items(snapshot: dict) -> list[str]:
    alerts: list[str] = []
    for ticker, position in _rank_portfolio_positions(snapshot):
        fundamentals = _ensure_asset_fundamentals(snapshot, ticker)
        vacancy = fundamentals.get("vacancy_percent")
        if vacancy is None:
            continue
        try:
            vacancy_value = float(vacancy)
        except Exception:
            continue
        if vacancy_value < 10:
            continue
        label = str(fundamentals.get("vacancy") or _format_percent(vacancy_value, digits=1)).strip()
        weight = position.get("portfolio_percentage")
        suffix = f", peso {weight}" if weight else ""
        alerts.append(f"{ticker} com vacância em {label}{suffix}")
    return alerts


def _volatility_alert_items(snapshot: dict) -> list[str]:
    alerts: list[str] = []
    for ticker, position in _rank_portfolio_positions(snapshot):
        fundamentals = _ensure_asset_fundamentals(snapshot, ticker)
        change = fundamentals.get("regular_market_change_percent")
        if change is None:
            change = _parse_percent_value(position.get("variation"))
        try:
            change_value = float(change)
        except Exception:
            continue
        threshold = 4.0 if str(position.get("category") or "").lower().startswith("cript") else 3.0
        if abs(change_value) < threshold:
            continue
        direction = "alta" if change_value > 0 else "queda"
        alerts.append(f"{ticker} em {direction} de {_format_percent(abs(change_value), digits=1)}")
    return alerts


def _portfolio_fii_dy_answer(snapshot: dict) -> str:
    return portfolio_fii_dy_answer(
        snapshot,
        rank_portfolio_positions=_rank_portfolio_positions,
        ensure_asset_fundamentals=_ensure_asset_fundamentals,
        is_probable_fii_ticker=_is_probable_fii_ticker,
        category_breakdown=_category_breakdown,
        unresolved_category_counts=_unresolved_category_counts,
    )


def _portfolio_attention_items(snapshot: dict) -> list[dict]:
    return portfolio_attention_items(
        snapshot,
        asset_positions=_asset_positions,
        effective_price_ceiling_fn=_effective_price_ceiling,
    )


def _position_quick_opinion(snapshot: dict, ticker: str, position: dict) -> str:
    return position_quick_opinion(
        snapshot,
        ticker,
        position,
        effective_price_ceiling_fn=_effective_price_ceiling,
    )


def _position_action_stance(snapshot: dict, ticker: str, position: dict) -> str:
    return position_action_stance(
        snapshot,
        ticker,
        position,
        effective_price_ceiling_fn=_effective_price_ceiling,
    )


def _external_asset_opinion(ticker: str, fundamentals: dict) -> tuple[str, str]:
    return external_asset_opinion(
        ticker,
        fundamentals,
        external_effective_price_ceiling=_external_effective_price_ceiling,
    )


def _format_external_asset_reading(ticker: str, fundamentals: dict) -> str:
    return format_external_asset_reading(
        ticker,
        fundamentals,
        get_asset_strategy=get_asset_strategy,
        external_effective_price_ceiling=_external_effective_price_ceiling,
        external_asset_opinion_fn=_external_asset_opinion,
    )


def _ticker_dividend_events(snapshot: dict, ticker: str) -> list[dict]:
    return ticker_dividend_events(snapshot, ticker, _ensure_asset_fundamentals)


def _format_dividend_event(ticker: str, event: dict) -> str:
    return format_dividend_event(ticker, event)


def _format_dividend_event_brief(ticker: str, event: dict) -> str:
    return format_dividend_event_brief(ticker, event)


def _portfolio_dividend_schedule(snapshot: dict, limit: int = 5) -> list[dict]:
    return portfolio_dividend_schedule(
        snapshot,
        rank_portfolio_positions=_rank_portfolio_positions,
        ensure_asset_fundamentals=_ensure_asset_fundamentals,
        limit=limit,
    )


def _portfolio_dividend_schedule_answer(snapshot: dict) -> str:
    return portfolio_dividend_schedule_answer(
        snapshot,
        rank_portfolio_positions=_rank_portfolio_positions,
        ensure_asset_fundamentals=_ensure_asset_fundamentals,
        unresolved_category_counts=_unresolved_category_counts,
    )


def format_upcoming_dividend_brief(
    limit: int = 2,
    *,
    max_days_until_payment: int | None = None,
    today=None,
) -> str:
    snapshot = load_investment_snapshot()
    return upcoming_dividend_brief(
        snapshot,
        rank_portfolio_positions=_rank_portfolio_positions,
        ensure_asset_fundamentals=_ensure_asset_fundamentals,
        limit=limit,
        max_days_until_payment=max_days_until_payment,
        today=today,
    )


def _clean_news_lead(text: str, ticker: str) -> str:
    return clean_news_lead(text, ticker)


def _portfolio_news_digest(
    snapshot: dict,
    limit_assets: int = 4,
    limit_summaries: int = 2,
    *,
    only_new: bool = False,
    mark_seen: bool = False,
) -> list[str]:
    return portfolio_news_digest(
        snapshot,
        investment_news_candidates=_investment_news_candidates,
        ensure_asset_fundamentals=_ensure_asset_fundamentals,
        get_asset_strategy=get_asset_strategy,
        summarize_asset_news=summarize_asset_news,
        normalize=_normalize,
        news_fingerprint=_news_fingerprint,
        load_seen_state=_news_seen_state,
        save_seen_state=_save_news_seen_state,
        limit_assets=limit_assets,
        limit_summaries=limit_summaries,
        only_new=only_new,
        mark_seen=mark_seen,
    )


def _compact_report_news(news_text: str, max_chars: int = 230) -> str:
    return compact_report_news(news_text, max_chars=max_chars)


def _portfolio_monitor_digest(snapshot: dict) -> str:
    return portfolio_monitor_digest(
        snapshot,
        portfolio_attention_items=_portfolio_attention_items,
        portfolio_items_above_ceiling=_portfolio_items_above_ceiling,
        material_price_ceiling_items=lambda items: _material_price_ceiling_items(items, threshold_percent=2.0),
        vacancy_alert_items=_vacancy_alert_items,
        volatility_alert_items=_volatility_alert_items,
        portfolio_dividend_schedule=_portfolio_dividend_schedule,
        format_dividend_event=_format_dividend_event,
        portfolio_news_digest=_portfolio_news_digest,
        filter_new_signal_texts=_filter_new_signal_texts,
        format_percent=_format_percent,
    )


def _format_position_reading(snapshot: dict, ticker: str, position: dict) -> str:
    return format_position_reading(
        snapshot,
        ticker,
        position,
        get_asset_strategy=get_asset_strategy,
        asset_fundamentals=_asset_fundamentals,
        effective_price_ceiling=_effective_price_ceiling,
        position_quick_opinion=_position_quick_opinion,
        position_action_stance=_position_action_stance,
    )


def _looks_like_broader_investment_question(normalized: str) -> bool:
    broader_terms = {
        "vale a pena",
        "bom ativo",
        "ativo bom",
        "acha de",
        "isso e bom",
        "isso e ruim",
        "esta bom",
        "esta ruim",
        "subindo",
        "caindo",
        "tendencia",
        "cenario",
        "leitura",
        "avaliacao",
        "analise",
        "analisar",
        "opiniao",
        "risco",
        "riscos",
        "tese",
        "comprar",
        "vender",
        "compra",
        "venda",
        "barato",
        "caro",
        "preco teto",
        "preço teto",
        "abaixo do meu preco teto",
        "abaixo do meu preço teto",
        "acima do meu preco teto",
        "acima do meu preço teto",
        "qual sua leitura",
        "o que voce acha",
        "o que você acha",
        "me fala mais",
        "me fale mais",
        "explica melhor",
        "me explica melhor",
        "momento de compra",
        "momento de venda",
    }
    return any(term in normalized for term in broader_terms)


def _looks_like_climate_investment_question(normalized: str) -> bool:
    return any(
        term in normalized
        for term in {
            "el nino",
            "la nina",
            "clima",
            "seca",
            "chuva",
            "safra",
            "estiagem",
            "fenomeno climatico",
            "fenomeno climático",
        }
    )


def _recent_climate_context_is_active() -> bool:
    try:
        from memory.ui_state import load_ui_state

        state = load_ui_state()
    except Exception:
        state = {}
    if not isinstance(state, dict):
        return False
    recent_text = " ".join(
        str(state.get(key) or "")
        for key in ("last_heard", "last_response", "last_command")
    )
    return _looks_like_climate_investment_question(_normalize(recent_text))


def _expand_investment_followup_question(question: str) -> str:
    normalized = _normalize(question)
    if _looks_like_climate_investment_question(normalized):
        return question
    if not any(term in normalized for term in {"afetado", "afetada", "afeta", "impacto"}):
        return question
    if not _recent_climate_context_is_active():
        return question
    return f"como o el nino afeta {question}"


def _build_local_investment_reading(question: str, snapshot: dict) -> str:
    return build_local_investment_reading(
        question,
        snapshot,
        get_asset_strategy=get_asset_strategy,
        asset_positions=_asset_positions,
        asset_fundamentals=_asset_fundamentals,
        extract_question_ticker=_extract_question_ticker,
        extract_ticker=_extract_ticker,
        extract_snapshot_direction=_extract_snapshot_direction,
        extract_current_price=_extract_current_price,
        normalize=_normalize,
        mentions_price_ceiling=_mentions_price_ceiling,
        effective_price_ceiling=_effective_price_ceiling,
    )


def _ask_grounded_investment_reading(question: str, snapshot: dict) -> str | None:
    return ask_grounded_investment_reading(
        question,
        snapshot,
        gemini_api_key=GEMINI_API_KEY,
        ask_gemini_grounded_model=ask_gemini_grounded_model,
        get_asset_strategy=get_asset_strategy,
        asset_fundamentals=_asset_fundamentals,
        extract_question_ticker=_extract_question_ticker,
        extract_ticker=_extract_ticker,
    )


def _ask_grounded_asset_news(question: str, ticker: str, snapshot: dict) -> str | None:
    return ask_grounded_asset_news(
        question,
        ticker,
        gemini_api_key=GEMINI_API_KEY,
        ask_gemini_grounded_model=ask_gemini_grounded_model,
        get_asset_strategy=get_asset_strategy,
    )


def _asset_news_answer(question: str, ticker: str, snapshot: dict, fundamentals: dict | None = None) -> str | None:
    return asset_news_answer(
        question,
        ticker,
        snapshot,
        fundamentals,
        get_asset_strategy=get_asset_strategy,
        summarize_asset_news=summarize_asset_news,
        ask_grounded_asset_news_fn=_ask_grounded_asset_news,
    )


def save_investment_snapshot(
    summary: str,
    metrics: list[str] | None = None,
    lines: list[str] | None = None,
    page_url: str = "",
    page_title: str = "",
    extra: dict | None = None,
):
    return save_investment_snapshot_payload(
        INVESTMENT_SNAPSHOT_PATH,
        summary=summary,
        metrics=metrics,
        lines=lines,
        page_url=page_url,
        page_title=page_title,
        extra=extra,
        extract_metric_map=_extract_metric_map,
        sync_portfolio_snapshot_note=sync_portfolio_snapshot_note,
    )


def load_investment_snapshot() -> dict:
    return load_investment_snapshot_payload(INVESTMENT_SNAPSHOT_PATH)


def format_investment_snapshot_summary() -> str:
    snapshot = load_investment_snapshot()
    updated_at = float(snapshot.get("updated_at") or 0)
    summary = str(snapshot.get("summary", "")).strip()
    metric_map = snapshot.get("metric_map") or {}

    if not updated_at and not summary:
        return "Ainda não tenho uma carteira salva localmente. Abra o Investidor10 uma vez e peça para atualizar os investimentos."

    key_order = ("patrimonio", "valor investido", "valor atual", "rentabilidade", "proventos")
    highlights = [f"{label}: {metric_map[label]}" for label in key_order if metric_map.get(label)]
    if highlights:
        return "Carteira atualizada. " + "; ".join(highlights) + "."

    if summary:
        return "Carteira atualizada. " + summary + "."

    return "Tenho uma carteira atualizada, mas ainda com poucos dados úteis extraídos."


def format_investment_financial_report(
    *,
    max_days_until_dividend: int | None = None,
    today=None,
) -> str:
    snapshot = load_investment_snapshot()
    return investment_financial_report(
        snapshot,
        category_breakdown=_category_breakdown,
        portfolio_attention_items=_portfolio_attention_items,
        portfolio_items_above_ceiling=_portfolio_items_above_ceiling,
        material_price_ceiling_items=lambda items: _material_price_ceiling_items(items, threshold_percent=2.0),
        vacancy_alert_items=_vacancy_alert_items,
        volatility_alert_items=_volatility_alert_items,
        portfolio_dividend_schedule=_portfolio_dividend_schedule,
        format_dividend_event_brief=_format_dividend_event_brief,
        portfolio_news_digest=_portfolio_news_digest,
        compact_report_news=_compact_report_news,
        filter_new_signal_texts=_filter_new_signal_texts,
        format_percent=_format_percent,
        max_days_until_dividend=max_days_until_dividend,
        today=today,
    )


def format_investment_active_radar_brief(
    *,
    max_days_until_dividend: int | None = None,
    today=None,
) -> str:
    snapshot = load_investment_snapshot()
    return investment_active_radar_brief(
        snapshot,
        portfolio_attention_items=_portfolio_attention_items,
        portfolio_items_above_ceiling=_portfolio_items_above_ceiling,
        material_price_ceiling_items=lambda items: _material_price_ceiling_items(items, threshold_percent=2.0),
        volatility_alert_items=_volatility_alert_items,
        portfolio_dividend_schedule=_portfolio_dividend_schedule,
        format_dividend_event_brief=_format_dividend_event_brief,
        portfolio_news_digest=_portfolio_news_digest,
        compact_report_news=_compact_report_news,
        format_percent=_format_percent,
        max_days_until_dividend=max_days_until_dividend,
        today=today,
    )


def format_investment_daily_change_report() -> str:
    snapshot = load_investment_snapshot()
    history_payload = _load_json(INVESTMENT_SNAPSHOT_PATH.with_name("investment_snapshot_history.json"))
    history_items = history_payload.get("items") if isinstance(history_payload, dict) else []
    if not isinstance(history_items, list):
        history_items = []
    return investment_daily_change_report(
        snapshot,
        history_items,
        portfolio_items_above_ceiling=_portfolio_items_above_ceiling,
        portfolio_dividend_schedule=_portfolio_dividend_schedule,
        format_dividend_event_brief=_format_dividend_event_brief,
        portfolio_news_digest=_portfolio_news_digest,
        parse_percent_value=_parse_percent_value,
        format_brl=_format_brl,
        format_percent=_format_percent,
    )


def _answer_investment_snapshot_question_base(question: str) -> str:
    snapshot = load_investment_snapshot()
    updated_at = float(snapshot.get("updated_at") or 0)
    summary = str(snapshot.get("summary", "")).strip()
    metric_map = snapshot.get("metric_map") or {}
    normalized = _normalize(question)
    question_ticker = _extract_question_ticker(question)
    strategy = get_asset_strategy(question_ticker) if question_ticker else {}
    asset_positions = _asset_positions(snapshot)
    asset_position = asset_positions.get(question_ticker, {}) if question_ticker else {}

    if _looks_like_climate_investment_question(normalized):
        if not updated_at and not summary:
            return answer_empty_snapshot()
        return _build_local_investment_reading(question, snapshot)

    if question_ticker and _looks_like_broader_investment_question(normalized) and asset_position:
        return _format_position_reading(snapshot, question_ticker, asset_position)

    if question_ticker and _mentions_price_ceiling(normalized):
        return answer_manual_price_ceiling(
            snapshot,
            question_ticker,
            asset_position,
            strategy,
            extract_current_price=_extract_current_price,
        )

    if "margem de segurança" in normalized or "margem de seguranca" in normalized:
        return answer_auto_ceiling_settings(get_auto_ceiling_settings())

    if question_ticker and "watchlist" in normalized:
        return answer_watchlist_status(question_ticker, strategy)

    if question_ticker and "tese" in normalized:
        return answer_thesis_status(question_ticker, strategy)

    if question_ticker and asset_positions and not asset_position:
        return answer_missing_ticker_in_portfolio(
            question_ticker,
            updated_at,
            format_timestamp_natural=_format_timestamp_natural,
        )

    if not updated_at and not summary:
        return answer_empty_snapshot()

    if any(token in normalized for token in ("quando", "atualizado", "atualizacao", "salvo", "snapshot")):
        return answer_snapshot_updated_at(updated_at, format_timestamp_natural=_format_timestamp_natural)

    if question_ticker and any(term in normalized for term in {"caro", "barato", "criterio", "critério"}):
        return answer_price_criterion(
            snapshot,
            question_ticker,
            asset_position,
            effective_price_ceiling=_effective_price_ceiling,
        )

    if "quais ativos" in normalized and ("acima do meu preco teto" in normalized or "acima do meu preço teto" in normalized):
        return answer_manual_assets_above_ceiling(
            snapshot,
            portfolio_items_above_ceiling=_portfolio_items_above_ceiling,
        )

    if "quais ativos" in normalized and "negativos" in normalized:
        return answer_negative_assets(snapshot, asset_positions=_asset_positions)

    if "merecem atencao" in normalized or "merecem atenção" in normalized:
        return answer_attention_assets(
            snapshot,
            portfolio_attention_items=_portfolio_attention_items,
            position_action_stance=_position_action_stance,
            asset_positions=_asset_positions,
        )

    metric_answer = answer_metric_question(normalized, question_ticker, asset_position, metric_map)
    if metric_answer:
        return metric_answer

    if _looks_like_broader_investment_question(normalized):
        if asset_position:
            grounded = _ask_grounded_investment_reading(question, snapshot)
            if grounded:
                return grounded
            return _format_position_reading(snapshot, question_ticker, asset_position)
        grounded = _ask_grounded_investment_reading(question, snapshot)
        if grounded:
            return grounded
        return _build_local_investment_reading(question, snapshot)

    if summary:
        return "Carteira atualizada. " + summary

    return "Tenho uma carteira atualizada, mas não encontrei essa informação de forma confiável nela."

def answer_investment_snapshot_question(question: str) -> str:
    question = _expand_investment_followup_question(question)
    snapshot = load_investment_snapshot()
    normalized = _normalize(question)
    question_ticker = _extract_question_ticker(question)
    asset_positions = _asset_positions(snapshot)
    asset_position = asset_positions.get(question_ticker, {}) if question_ticker else {}
    strategy = get_asset_strategy(question_ticker) if question_ticker else {}
    fundamentals = _ensure_asset_fundamentals(snapshot, question_ticker) if question_ticker else {}

    if question_ticker and not asset_position and fundamentals and _looks_like_broader_investment_question(normalized):
        return _format_external_asset_reading(question_ticker, fundamentals)

    if _contains_investment_phrase(
        normalized,
        "agenda de dividendos",
        "dividendos agendados",
        "proximos dividendos",
        "proximos proventos",
        "meus dividendos",
        "meus proventos",
        "proximo dividendo",
        "data ex",
        "data com",
    ):
        return answer_dividend_question(
            snapshot,
            question_ticker,
            fundamentals,
            ticker_dividend_events=_ticker_dividend_events,
            format_dividend_event=_format_dividend_event,
            portfolio_dividend_schedule_answer=_portfolio_dividend_schedule_answer,
        )

    if _contains_investment_phrase(
        normalized,
        "noticias confiaveis",
        "noticias dos meus ativos",
        "noticias da carteira",
        "alguma noticia sobre minha carteira",
        "tem alguma noticia sobre minha carteira",
        "tem noticia sobre minha carteira",
        "fatos relevantes da carteira",
        "fato relevante da carteira",
        "noticias relevantes",
    ):
        return answer_portfolio_news_question(snapshot, portfolio_news_digest=_portfolio_news_digest)

    if _contains_investment_phrase(normalized, "monitoramento", "monitorar carteira", "radar da carteira"):
        return _portfolio_monitor_digest(snapshot)

    if _contains_investment_phrase(normalized, "dy", "yield") and _contains_investment_phrase(
        normalized,
        "fii",
        "fiis",
        "fundo imobiliario",
        "fundos imobiliarios",
    ):
        return _portfolio_fii_dy_answer(snapshot)

    if question_ticker and _contains_investment_phrase(normalized, "dy", "dividend yield", "yield"):
        return answer_ticker_yield(question_ticker, fundamentals)

    if question_ticker and _contains_investment_phrase(normalized, "cotacao", "cotação", "cotaçao"):
        return answer_ticker_quote(question_ticker, asset_position, fundamentals)

    if question_ticker and _contains_investment_phrase(normalized, "preco medio", "preço medio", "preço médio", "preco médio"):
        return answer_ticker_average_price(question_ticker, asset_position)

    if question_ticker and _contains_investment_phrase(normalized, "variacao do dia", "variação do dia", "variacao hoje", "variação hoje", "no dia", "hoje"):
        return answer_ticker_day_variation(question_ticker, asset_position)

    if question_ticker and _contains_investment_phrase(normalized, "subindo", "caindo", "variacao", "variação", "alta", "queda"):
        return answer_ticker_trend(question_ticker, asset_position)

    if question_ticker and _contains_investment_phrase(normalized, "dividendos agendados", "proventos agendados", "dividendos previstos", "dividendos programados", "proximo dividendo", "próximo dividendo", "data ex", "data com"):
        return f"Ainda não tenho agenda de dividendos integrada para {question_ticker}. Hoje eu consigo ler proventos e DY salvos, mas não a próxima data com confiança."

    if question_ticker and _contains_investment_phrase(normalized, "fato relevante", "noticia", "notícias", "noticias", "relevante", "novidade"):
        news_answer = _asset_news_answer(question, question_ticker, snapshot, fundamentals)
        if news_answer:
            return news_answer
        return f"Ainda não consegui buscar notícias ou fatos relevantes confiáveis para {question_ticker}."

    if question_ticker and _mentions_price_ceiling(normalized):
        answer = answer_auto_price_ceiling(
            snapshot,
            question_ticker,
            asset_position,
            strategy,
            extract_current_price=_extract_current_price,
            effective_price_ceiling=_effective_price_ceiling,
        )
        if answer:
            return answer

    if "quais ativos" in normalized and ("acima do meu preco teto" in normalized or "acima do meu preço teto" in normalized):
        return answer_assets_above_ceiling(
            snapshot,
            portfolio_items_above_ceiling=_portfolio_items_above_ceiling,
        )

    if question_ticker and _contains_investment_phrase(normalized, "dividendos agendados", "proventos agendados", "dividendos previstos", "dividendos programados", "proximo dividendo", "data ex", "data com"):
        return answer_dividend_question(
            snapshot,
            question_ticker,
            fundamentals,
            ticker_dividend_events=_ticker_dividend_events,
            format_dividend_event=_format_dividend_event,
            portfolio_dividend_schedule_answer=_portfolio_dividend_schedule_answer,
        )

    return _answer_investment_snapshot_question_base(question)
