import json
import hashlib
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from config import GEMINI_API_KEY
from llm.gemini_client import ask_gemini_grounded_model
from memory.investment_asset_fundamentals import fetch_asset_fundamentals
from memory.obsidian_sync import sync_portfolio_snapshot_note
from memory.news_api import summarize_asset_news
from memory.investment_strategy import (
    calculate_auto_price_ceiling,
    get_asset_strategy,
    get_auto_ceiling_settings,
    load_investment_strategy,
)


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
INVESTMENT_SNAPSHOT_PATH = MEMORY_DIR / "investment_snapshot.json"
INVESTMENT_NEWS_SEEN_PATH = MEMORY_DIR / "investment_news_seen.json"
INVESTMENT_SIGNAL_SEEN_PATH = MEMORY_DIR / "investment_signal_seen.json"

VALUE_RE = re.compile(
    r"[-+]?\d+(?:,\d+)?\s*%|(?:r\$\s*)?[-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2})",
    re.IGNORECASE,
)

LABEL_HINTS = {
    "patrimonio": ("patrimonio total", "patrimonio", "patrimônio total", "patrimônio"),
    "valor investido": ("valor investido",),
    "valor atual": ("valor atual",),
    "rentabilidade": ("rentabilidade",),
    "proventos": ("proventos", "dividendos"),
    "saldo": ("saldo",),
    "lucro": ("lucro",),
    "prejuizo": ("prejuizo", "prejuízo"),
    "aporte": ("aporte",),
    "preco medio": ("preco medio", "preço médio", "preço medio"),
    "cotacao": ("cotacao", "cotação"),
    "variacao": ("variacao", "variação", "alta", "queda", "valorizacao", "desvalorizacao"),
}


def _save_json(path: Path, payload: dict):
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _news_seen_state() -> dict:
    data = _load_json(INVESTMENT_NEWS_SEEN_PATH)
    return data if isinstance(data, dict) else {}


def _save_news_seen_state(state: dict) -> None:
    if not isinstance(state, dict):
        return
    try:
        _save_json(INVESTMENT_NEWS_SEEN_PATH, state)
    except Exception:
        pass


def _signal_seen_state() -> dict:
    data = _load_json(INVESTMENT_SIGNAL_SEEN_PATH)
    return data if isinstance(data, dict) else {}


def _save_signal_seen_state(state: dict) -> None:
    if not isinstance(state, dict):
        return
    try:
        _save_json(INVESTMENT_SIGNAL_SEEN_PATH, state)
    except Exception:
        pass


def _news_fingerprint(text: str) -> str:
    normalized = _normalize(text)
    if not normalized:
        return ""
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def _signal_fingerprint(kind: str, text: str) -> str:
    return _news_fingerprint(f"{kind}: {text}")


def _filter_new_signal_texts(kind: str, texts: list[str], *, only_new: bool = False, mark_seen: bool = False) -> list[str]:
    if not only_new and not mark_seen:
        return texts

    state = _signal_seen_state()
    seen_by_kind = state.get(kind)
    if not isinstance(seen_by_kind, list):
        seen_by_kind = []
    seen_hashes = set(str(item) for item in seen_by_kind)
    fresh: list[str] = []
    new_hashes: list[str] = []

    for text in texts:
        fingerprint = _signal_fingerprint(kind, text)
        if only_new and fingerprint and fingerprint in seen_hashes:
            continue
        fresh.append(text)
        if fingerprint:
            new_hashes.append(fingerprint)

    if mark_seen and new_hashes:
        combined = list(dict.fromkeys([*seen_hashes, *new_hashes]))
        state[kind] = combined[-80:]
        state["updated_at"] = time.time()
        _save_signal_seen_state(state)

    return fresh


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
    if value is None:
        return ""
    formatted = f"{float(value):,.2f}"
    return "R$ " + formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(value: float | None, digits: int = 1) -> str:
    if value is None:
        return ""
    formatted = f"{float(value):,.{digits}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".") + "%"


def _snapshot_blob(snapshot: dict) -> str:
    return " ".join(
        [
            str(snapshot.get("page_title", "")),
            str(snapshot.get("summary", "")),
            *[str(item) for item in (snapshot.get("metrics") or [])],
            *[str(item) for item in (snapshot.get("lines") or [])],
        ]
    )


def _extract_metric_map(metrics: list[str] | None, lines: list[str] | None) -> dict[str, str]:
    metric_map: dict[str, str] = {}
    candidates = list(metrics or []) + list(lines or [])

    for raw_line in candidates:
        line = re.sub(r"\s+", " ", str(raw_line or "")).strip()
        if not line:
            continue
        normalized = _normalize(line)
        values = VALUE_RE.findall(line)
        if not values:
            continue

        for canonical, hints in LABEL_HINTS.items():
            if canonical in metric_map:
                continue
            if any(hint in normalized for hint in hints):
                metric_map[canonical] = values[0].strip()
                break

    return metric_map


def _extract_ticker(snapshot: dict) -> str:
    match = re.search(r"\b([A-Z]{4}\d{1,2})\b", _snapshot_blob(snapshot))
    return match.group(1).upper() if match else ""


def _extract_question_ticker(question: str) -> str:
    text = str(question or "")
    match = re.search(r"\b([A-Za-z]{4,5}\d{1,2})\b", text)
    if match:
        return match.group(1).upper()
    for symbol in ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE"):
        if re.search(rf"\b{symbol}(?:[-/](?:BRL|USD|USDT))?\b", text, flags=re.I):
            return symbol
    return ""


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
    normalized = _normalize(_snapshot_blob(snapshot))
    raw_blob = _snapshot_blob(snapshot)

    if "0,00%" in raw_blob or "0 00 %" in normalized:
        return "sem movimento relevante no recorte visível"
    if any(term in normalized for term in {"arrow upward", "alta", "subindo", "valorizacao"}):
        return "em alta no recorte visível"
    if any(term in normalized for term in {"arrow downward", "queda", "caindo", "desvalorizacao"}):
        return "em queda no recorte visível"
    return ""


def _parse_currency_value(text: str) -> float | None:
    cleaned = str(text or "").strip().lower().replace("r$", "").replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_percent_value(text: str) -> float | None:
    cleaned = str(text or "").strip().replace("%", "").replace(" ", "")
    if not cleaned:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


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
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone()
    except Exception:
        return None


def _format_day_month(value: str) -> str:
    parsed = _parse_iso_datetime(value)
    if not parsed:
        return ""
    return parsed.strftime("%d/%m")


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
    reference_name = str(strategy.get("auto_ceiling_reference", "preco_medio")).strip()
    if reference_name == "cotacao_atual":
        return _parse_currency_value(position.get("current_price"))
    return _parse_currency_value(position.get("average_price")) or _parse_currency_value(position.get("current_price"))


def _effective_price_ceiling(snapshot: dict, ticker: str, position: dict) -> tuple[float | None, str]:
    strategy = get_asset_strategy(ticker)
    manual_ceiling = strategy.get("price_ceiling")
    if manual_ceiling is not None:
        return float(manual_ceiling), "manual"

    if not strategy.get("auto_ceiling_enabled"):
        return None, "none"

    if str(strategy.get("auto_ceiling_method", "")).strip() == "yield_alvo":
        fundamentals = _asset_fundamentals(snapshot).get(ticker, {})
        annual_dividend = fundamentals.get("annual_dividend_estimate_per_share")
        target_yield = strategy.get("auto_ceiling_target_yield_percent")
        if annual_dividend and target_yield:
            try:
                ceiling = float(annual_dividend) / (float(target_yield) / 100.0)
                if ceiling > 0:
                    return ceiling, "automatic_yield"
            except Exception:
                pass

    reference_price = _resolve_reference_price(position, strategy)
    auto_ceiling = calculate_auto_price_ceiling(reference_price, strategy.get("auto_ceiling_margin_percent"))
    if auto_ceiling is None:
        return None, "none"
    return float(auto_ceiling), "automatic"


def _external_effective_price_ceiling(ticker: str, fundamentals: dict) -> tuple[float | None, str]:
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


def _portfolio_items_above_ceiling(snapshot: dict) -> list[dict]:
    results: list[dict] = []
    for ticker, position in _asset_positions(snapshot).items():
        current_price = _parse_currency_value(position.get("current_price"))
        ceiling, source = _effective_price_ceiling(snapshot, ticker, position)
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


def _is_price_ceiling_alert_material(item: dict, *, threshold_percent: float = 2.0) -> bool:
    ticker = str(item.get("ticker") or "").upper()
    if not ticker:
        return False

    current_price = item.get("current_price")
    ceiling = item.get("ceiling")
    premium_percent = item.get("premium_percent")
    state = _signal_seen_state()
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
    _save_signal_seen_state(state)
    return material


def _material_price_ceiling_items(items: list[dict], *, threshold_percent: float = 2.0) -> list[dict]:
    return [
        item
        for item in items
        if _is_price_ceiling_alert_material(item, threshold_percent=threshold_percent)
    ]


def _watchlist_tickers_not_in_portfolio(snapshot: dict) -> list[str]:
    strategy = load_investment_strategy()
    watchlist = [str(item).upper() for item in strategy.get("watchlist", []) if str(item).strip()]
    portfolio = set(_asset_positions(snapshot).keys())
    return [ticker for ticker in dict.fromkeys(watchlist) if ticker and ticker not in portfolio]


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
        alerts.append(f"{ticker} com vacÃ¢ncia em {label}{suffix}")
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
    fii_rows: list[tuple[str, str, float]] = []
    weighted_sum = 0.0
    weight_total = 0.0

    for ticker, position in _rank_portfolio_positions(snapshot):
        fundamentals = _ensure_asset_fundamentals(snapshot, ticker)
        if not _is_probable_fii_ticker(ticker, fundamentals):
            continue
        dy_label = str(fundamentals.get("dividend_yield_current") or "").strip()
        dy_percent = fundamentals.get("dividend_yield_current_percent")
        if not dy_label or dy_percent in (None, ""):
            continue
        weight = _parse_percent_value(position.get("portfolio_percentage")) or 0.0
        fii_rows.append((ticker, dy_label, weight))
        weighted_sum += float(dy_percent) * weight
        weight_total += weight

    if fii_rows:
        listed = "; ".join(f"{ticker} em {dy}" for ticker, dy, _weight in fii_rows)
        if weight_total > 0:
            weighted_average = weighted_sum / weight_total
            return (
                f"O DY dos seus FIIs salvos hoje está assim: {listed}. "
                f"Pelo peso atual desse bloco, o DY médio ponderado fica perto de {_format_percent(weighted_average, digits=2)}."
            )
        return f"O DY dos seus FIIs salvos hoje está assim: {listed}."

    breakdown = _category_breakdown(snapshot)
    fii_share = str(breakdown.get("FIIs") or "").strip()
    if fii_share:
        unresolved = _unresolved_category_counts(snapshot).get("FIIs", {})
        reported = int(unresolved.get("reported") or 0) if isinstance(unresolved, dict) else 0
        captured = int(unresolved.get("captured") or 0) if isinstance(unresolved, dict) else 0
        detail_parts = []
        if reported:
            detail_parts.append(f"a fonte pública reporta {reported} ativos nesse bloco")
        if captured:
            detail_parts.append(f"e eu consegui individualizar {captured}")
        details = ""
        if detail_parts:
            details = " Hoje, " + ", ".join(detail_parts) + "."
        return (
            f"Hoje eu sei que FIIs representam {fii_share} da sua carteira, mas a carteira pública ainda expõe esse bloco de forma agregada.{details} "
            "Então eu ainda não consigo te dar o DY dos seus FIIs um por um com confiança. "
            "Se você me disser um ticker específico, como XPML11 ou VGIA11, eu já consigo analisar DY, preço e dividendos dele."
        )

    return "No snapshot atual, eu não consegui identificar FIIs individualizados na carteira."


def _portfolio_fii_dy_answer(snapshot: dict) -> str:
    fii_rows: list[tuple[str, str, float]] = []
    weighted_sum = 0.0
    weight_total = 0.0

    for ticker, position in _rank_portfolio_positions(snapshot):
        fundamentals = _ensure_asset_fundamentals(snapshot, ticker)
        if not _is_probable_fii_ticker(ticker, fundamentals):
            continue
        dy_label = str(fundamentals.get("dividend_yield_current") or "").strip()
        dy_percent = fundamentals.get("dividend_yield_current_percent")
        if not dy_label or dy_percent in (None, ""):
            continue
        weight = _parse_percent_value(position.get("portfolio_percentage")) or 0.0
        fii_rows.append((ticker, dy_label, weight))
        weighted_sum += float(dy_percent) * weight
        weight_total += weight

    if fii_rows:
        listed = "; ".join(f"{ticker} em {dy}" for ticker, dy, _weight in fii_rows)
        if weight_total > 0:
            weighted_average = weighted_sum / weight_total
            return (
                f"O DY dos seus FIIs salvos hoje está assim: {listed}. "
                f"Pelo peso atual desse bloco, o DY médio ponderado fica perto de {_format_percent(weighted_average, digits=2)}."
            )
        return f"O DY dos seus FIIs salvos hoje está assim: {listed}."

    breakdown = _category_breakdown(snapshot)
    fii_share = str(breakdown.get("FIIs") or "").strip()
    if fii_share:
        unresolved = _unresolved_category_counts(snapshot).get("FIIs", {})
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


def _portfolio_attention_items(snapshot: dict) -> list[dict]:
    items: list[dict] = []
    for ticker, position in _asset_positions(snapshot).items():
        reasons: list[str] = []
        opinions: list[str] = []
        current_price = _parse_currency_value(position.get("current_price"))
        average_price = _parse_currency_value(position.get("average_price"))
        variation = _parse_percent_value(position.get("variation"))
        rentability = _parse_percent_value(position.get("rentability"))
        portfolio_percentage = _parse_percent_value(position.get("portfolio_percentage"))
        ideal_percentage = _parse_percent_value(position.get("ideal_percentage"))
        rating_text = str(position.get("rating", "")).strip()
        buy_more = str(position.get("buy_more", "")).strip().lower()

        ceiling, source = _effective_price_ceiling(snapshot, ticker, position)
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
        if average_price is not None and current_price is not None and current_price < average_price and buy_more == "não":
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


def _position_quick_opinion(snapshot: dict, ticker: str, position: dict) -> str:
    current_price = _parse_currency_value(position.get("current_price"))
    average_price = _parse_currency_value(position.get("average_price"))
    variation = _parse_percent_value(position.get("variation"))
    rentability = _parse_percent_value(position.get("rentability"))
    strategy = get_asset_strategy(ticker)
    ceiling, source = _effective_price_ceiling(snapshot, ticker, position)

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


def _position_action_stance(snapshot: dict, ticker: str, position: dict) -> str:
    current_price = _parse_currency_value(position.get("current_price"))
    average_price = _parse_currency_value(position.get("average_price"))
    variation = _parse_percent_value(position.get("variation"))
    rentability = _parse_percent_value(position.get("rentability"))
    ceiling, source = _effective_price_ceiling(snapshot, ticker, position)
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


def _external_asset_opinion(ticker: str, fundamentals: dict) -> tuple[str, str]:
    quote_value = fundamentals.get("quote_value")
    dy_percent = fundamentals.get("dividend_yield_current_percent")
    p_vp = _parse_percent_value(fundamentals.get("p_vp")) if isinstance(fundamentals.get("p_vp"), str) else None
    try:
        if p_vp is None and fundamentals.get("p_vp") not in (None, ""):
            p_vp = float(str(fundamentals.get("p_vp")).replace(".", "").replace(",", "."))
    except Exception:
        p_vp = None
    try:
        p_l = float(str(fundamentals.get("p_l")).replace(".", "").replace(",", ".")) if fundamentals.get("p_l") not in (None, "") else None
    except Exception:
        p_l = None
    ceiling, source = _external_effective_price_ceiling(ticker, fundamentals)

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


def _format_external_asset_reading(ticker: str, fundamentals: dict) -> str:
    strategy = get_asset_strategy(ticker)
    company_name = str(fundamentals.get("company_name") or "").strip()
    quote = str(fundamentals.get("quote") or "").strip()
    dy_current = str(fundamentals.get("dividend_yield_current") or "").strip()
    dy_average = str(fundamentals.get("dividend_yield_5y_average") or "").strip()
    p_vp = str(fundamentals.get("p_vp") or "").strip()
    p_l = str(fundamentals.get("p_l") or "").strip()
    ceiling, source = _external_effective_price_ceiling(ticker, fundamentals)
    opinion, stance = _external_asset_opinion(ticker, fundamentals)

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
            parts.append(f"Seu preço-teto salvo para {ticker} está em {_format_brl(ceiling)}.")
        elif source == "automatic_yield":
            parts.append(f"Pela base automática por yield alvo, o preço-teto estimado ficaria em {_format_brl(ceiling)}.")
        elif source == "automatic":
            parts.append(f"Pela base automática atual, o preço-teto estimado ficaria em {_format_brl(ceiling)}.")
    thesis = str(strategy.get("thesis", "")).strip()
    if thesis:
        parts.append(f"Sua tese curta salva para esse ativo é: {thesis}")
    if strategy.get("in_watchlist"):
        parts.append(f"{ticker} já está na sua watchlist.")
    parts.append(opinion)
    parts.append(stance)
    return " ".join(parts)


def _ticker_dividend_events(snapshot: dict, ticker: str) -> list[dict]:
    fundamentals = _ensure_asset_fundamentals(snapshot, ticker)
    events = fundamentals.get("next_dividend_events")
    if not isinstance(events, list):
        return []
    ranked_events: list[tuple[datetime, dict]] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        payment_date = _parse_iso_datetime(event.get("payment_date"))
        last_date_prior = _parse_iso_datetime(event.get("last_date_prior"))
        sort_key = payment_date or last_date_prior
        if not sort_key:
            continue
        ranked_events.append((sort_key, event))
    ranked_events.sort(key=lambda item: item[0])
    return [event for _, event in ranked_events]


def _format_dividend_event(ticker: str, event: dict) -> str:
    details: list[str] = []
    rate_value = _parse_currency_value(event.get("rate"))
    if rate_value is not None and rate_value > 1000:
        rate_value = rate_value / 1_000_000
    if rate_value is not None:
        details.append(f"valor de {_format_brl(rate_value)} por cota")
    payment_day = _format_day_month(event.get("payment_date"))
    if payment_day:
        details.append(f"pagamento em {payment_day}")
    last_date = _format_day_month(event.get("last_date_prior"))
    if last_date:
        details.append(f"data-com até {last_date}")
    label = str(event.get("label") or "").strip()
    prefix = f"{ticker}"
    if label:
        prefix += f" ({label})"
    if details:
        return prefix + ": " + ", ".join(details)
    return prefix


def _format_dividend_event_brief(ticker: str, event: dict) -> str:
    label = str(event.get("label") or "").strip()
    payment_day = _format_day_month(event.get("payment_date"))
    if label and payment_day:
        return f"{ticker} paga {label} em {payment_day}"
    if payment_day:
        return f"{ticker} paga em {payment_day}"
    if label:
        return f"{ticker} tem {label} no radar"
    return ticker


def _portfolio_dividend_schedule(snapshot: dict, limit: int = 5) -> list[dict]:
    events: list[dict] = []
    for ticker, position in _rank_portfolio_positions(snapshot):
        ticker_events = _ticker_dividend_events(snapshot, ticker)
        if not ticker_events:
            continue
        for event in ticker_events[:2]:
            sort_key = _parse_iso_datetime(event.get("payment_date")) or _parse_iso_datetime(event.get("last_date_prior"))
            if not sort_key:
                continue
            events.append(
                {
                    "ticker": ticker,
                    "event": event,
                    "sort_key": sort_key,
                    "portfolio_percentage": _parse_percent_value(position.get("portfolio_percentage")) or 0.0,
                }
            )
    events.sort(key=lambda item: (item["sort_key"], -item["portfolio_percentage"]))
    return events[: max(1, limit)]


def _portfolio_dividend_schedule_answer(snapshot: dict) -> str:
    events = _portfolio_dividend_schedule(snapshot, limit=5)
    if events:
        details = "; ".join(_format_dividend_event(item["ticker"], item["event"]) for item in events)
        return "Agenda de dividendos da carteira: " + details + "."

    unresolved = _unresolved_category_counts(snapshot)
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


def format_upcoming_dividend_brief(limit: int = 2) -> str:
    snapshot = load_investment_snapshot()
    events = _portfolio_dividend_schedule(snapshot, limit=max(1, int(limit)))
    if not events:
        return ""

    details = [
        _format_dividend_event_brief(item["ticker"], item["event"])
        for item in events
    ]
    details = [item for item in details if item]
    if not details:
        return ""
    return "Dividendos próximos: " + "; ".join(details) + "."


def _clean_news_lead(text: str, ticker: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    patterns = [
        rf"^encontrei sinais relevantes sobre {re.escape(ticker)}\.\s*",
        rf"^eu encontrei material sobre {re.escape(ticker)},\s*",
        rf"^o que apareceu sobre {re.escape(ticker)}\s*",
    ]
    for pattern in patterns:
        cleaned = re.sub(pattern, "", cleaned, flags=re.I)
    return cleaned.strip()


def _portfolio_news_digest(
    snapshot: dict,
    limit_assets: int = 4,
    limit_summaries: int = 2,
    *,
    only_new: bool = False,
    mark_seen: bool = False,
) -> list[str]:
    summaries: list[str] = []
    seen_state = _news_seen_state() if only_new or mark_seen else {}
    seen_hashes = set(str(item) for item in (seen_state.get("seen") or []))
    new_hashes: list[str] = []

    for ticker, scope, _position in _investment_news_candidates(snapshot, limit_assets):
        fundamentals = _ensure_asset_fundamentals(snapshot, ticker)
        company_name = str(fundamentals.get("company_name") or "").strip()
        thesis = str(get_asset_strategy(ticker).get("thesis") or "").strip()
        try:
            summary = summarize_asset_news(
                ticker,
                company_name=company_name,
                thesis=thesis,
                market_data=fundamentals,
            )
        except Exception:
            summary = None
        cleaned = _clean_news_lead(summary or "", ticker)
        if not cleaned:
            continue
        normalized_cleaned = _normalize(cleaned)
        if "nada com confianca suficiente" in normalized_cleaned:
            continue
        if "sensacionalista" in normalized_cleaned:
            continue
        if not any(
            term in normalized_cleaned
            for term in {
                "resultado",
                "lucro",
                "prejuizo",
                "dividendo",
                "provento",
                "jcp",
                "fato relevante",
                "guidance",
                "aquisicao",
                "fusao",
                "oferta",
                "captacao",
                "venda",
                "compra",
                "risco",
                "divida",
                "selic",
                "juros",
            }
        ):
            continue
        fingerprint = _news_fingerprint(f"{ticker}: {cleaned}")
        if only_new and fingerprint and fingerprint in seen_hashes:
            continue
        prefix = ticker if scope == "carteira" else f"{ticker} (watchlist)"
        summaries.append(f"{prefix}: {_compact_report_news(cleaned, max_chars=150)}")
        if fingerprint:
            new_hashes.append(fingerprint)
        if len(summaries) >= limit_summaries:
            break

    if mark_seen and new_hashes:
        combined = list(dict.fromkeys([*seen_hashes, *new_hashes]))
        seen_state["seen"] = combined[-80:]
        seen_state["updated_at"] = time.time()
        _save_news_seen_state(seen_state)
    return summaries


def _compact_report_news(news_text: str, max_chars: int = 230) -> str:
    text = re.sub(r"\s+", " ", str(news_text or "")).strip()
    if not text:
        return ""
    text = re.sub(r"\bIsso importa porque\b", "Relevância:", text, flags=re.I)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    compact = " ".join(sentence for sentence in sentences[:2] if sentence).strip()
    if not compact:
        compact = text
    if len(compact) <= max_chars:
        return compact
    trimmed = compact[:max_chars].rsplit(" ", 1)[0].strip()
    return trimmed.rstrip(".,;:") + "."


def _portfolio_monitor_digest(snapshot: dict) -> str:
    parts: list[str] = []

    attention_items = _portfolio_attention_items(snapshot)[:3]
    if attention_items:
        attention_text = []
        for item in attention_items:
            reason_text = ", ".join(item["reasons"][:2])
            opinion_text = ""
            opinions = item.get("opinions") or []
            if opinions:
                opinion_text = str(opinions[0]).strip()
            if opinion_text:
                attention_text.append(f"{item['ticker']} ({reason_text}); minha leitura: {opinion_text}")
            else:
                attention_text.append(f"{item['ticker']} ({reason_text})")
        attention_text = _filter_new_signal_texts("attention", attention_text, only_new=True, mark_seen=True)
        attention_text = attention_text[:3]
    else:
        attention_text = []
    if attention_text:
        parts.append("Pontos de atencao: " + "; ".join(attention_text) + ".")

    ceiling_items = _material_price_ceiling_items(_portfolio_items_above_ceiling(snapshot), threshold_percent=2.0)[:2]
    if ceiling_items:
        ceiling_text = []
        for item in ceiling_items:
            premium = _format_percent(item.get("premium_percent"), digits=1)
            ceiling_text.append(
                f"{item['ticker']} acima do teto em {premium}"
                if premium
                else f"{item['ticker']} acima do teto"
            )
        if ceiling_text:
            parts.append("Preco-teto com mudanca relevante: " + "; ".join(ceiling_text) + ".")

    vacancy_items = _filter_new_signal_texts(
        "vacancy",
        _vacancy_alert_items(snapshot),
        only_new=True,
        mark_seen=True,
    )[:2]
    if vacancy_items:
        parts.append("Vacancia no radar: " + "; ".join(vacancy_items) + ".")

    volatility_items = _filter_new_signal_texts(
        "volatility",
        _volatility_alert_items(snapshot),
        only_new=True,
        mark_seen=True,
    )[:2]
    if volatility_items:
        parts.append("Volatilidade no radar: " + "; ".join(volatility_items) + ".")

    dividend_events = _portfolio_dividend_schedule(snapshot, limit=2)
    if dividend_events:
        dividend_items = [
            _format_dividend_event(item["ticker"], item["event"]) for item in dividend_events
        ]
        dividend_items = _filter_new_signal_texts(
            "dividend",
            dividend_items,
            only_new=True,
            mark_seen=True,
        )
        if dividend_items:
            parts.append("Proximos dividendos identificados: " + "; ".join(dividend_items[:2]) + ".")

    news_items = _portfolio_news_digest(snapshot, limit_assets=4, limit_summaries=1, only_new=True, mark_seen=True)
    if news_items:
        parts.append("Noticia que merece radar: " + news_items[0] + ".")

    if parts:
        return "Monitoramento atual da carteira: " + " ".join(parts)
    return "No momento, eu nao encontrei sinal forte de monitoramento alem do resumo normal da carteira."


def _format_position_reading(snapshot: dict, ticker: str, position: dict) -> str:
    strategy = get_asset_strategy(ticker)
    fundamentals = _asset_fundamentals(snapshot).get(ticker, {})
    current_price_text = str(position.get("current_price") or fundamentals.get("quote") or "").strip()
    current_price_value = _parse_currency_value(current_price_text)
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
        parts.append(f"Seu preço-teto salvo para {ticker} é {_format_brl(float(ceiling))}.")
        if current_price_value is not None:
            relation = "abaixo" if current_price_value <= float(ceiling) else "acima"
            parts.append(f"Pela cotação visível, ele está {relation} desse nível.")
    else:
        auto_ceiling, source = _effective_price_ceiling(snapshot, ticker, position)
        if auto_ceiling is not None:
            if source == "automatic_yield":
                target_yield = float(strategy.get("auto_ceiling_target_yield_percent", 8.0))
                parts.append(
                    f"Pela base automática por yield alvo de {target_yield:.0f}%, "
                    f"o preço-teto estimado ficaria em {_format_brl(auto_ceiling)}."
                )
            elif source == "automatic":
                margin = float(strategy.get("auto_ceiling_margin_percent", 8.0))
                parts.append(
                    f"Como referência automática, com margem de segurança de {margin:.0f}%, "
                    f"o preço-teto estimado ficaria em {_format_brl(auto_ceiling)}."
                )

    thesis = str(strategy.get("thesis", "")).strip()
    if thesis:
        parts.append(f"Sua tese curta salva para esse ativo é: {thesis}")

    if strategy.get("in_watchlist"):
        parts.append(f"{ticker} já está na sua watchlist.")

    parts.append(_position_quick_opinion(snapshot, ticker, position))
    parts.append(_position_action_stance(snapshot, ticker, position))
    return " ".join(parts)


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


def _build_local_investment_reading(question: str, snapshot: dict) -> str:
    metric_map = snapshot.get("metric_map") or {}
    ticker = _extract_question_ticker(question) or _extract_ticker(snapshot)
    direction = _extract_snapshot_direction(snapshot)
    summary = str(snapshot.get("summary", "")).strip()
    normalized_question = _normalize(question)
    strategy = get_asset_strategy(ticker) if ticker else {}
    price_ceiling = strategy.get("price_ceiling")
    thesis = str(strategy.get("thesis", "")).strip()
    in_watchlist = bool(strategy.get("in_watchlist"))
    current_price = _extract_current_price(snapshot)
    position = _asset_positions(snapshot).get(ticker, {}) if ticker else {}
    fundamentals = _asset_fundamentals(snapshot).get(ticker, {}) if ticker else {}

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
        parts.append(f"Seu preço-teto salvo para {asset_name} é {_format_brl(price_ceiling)}.")
        if current_price is not None:
            if current_price <= float(price_ceiling):
                parts.append("Pelo preço visível, ele está no ponto ou abaixo do seu preço-teto.")
            else:
                parts.append("Pelo preço visível, ele ainda está acima do seu preço-teto.")
    elif ticker and (current_price is not None or position):
        auto_ceiling, auto_source = _effective_price_ceiling(snapshot, ticker, position or {"current_price": _format_brl(current_price)})
        if auto_ceiling is not None:
            if auto_source == "automatic_yield":
                parts.append(
                    f"Pela base automática por yield alvo de {float(strategy.get('auto_ceiling_target_yield_percent', 8.0)):.0f}%, "
                    f"o preço-teto estimado ficaria em {_format_brl(auto_ceiling)}."
                )
            else:
                parts.append(
                    f"Como referência automática provisória, com margem de segurança de "
                    f"{float(strategy.get('auto_ceiling_margin_percent', 8.0)):.0f}%, "
                    f"o preço-teto estimado ficaria em {_format_brl(auto_ceiling)}."
                )
    elif _mentions_price_ceiling(normalized_question):
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


def _ask_grounded_investment_reading(question: str, snapshot: dict) -> str | None:
    if not GEMINI_API_KEY:
        return None

    metric_map = snapshot.get("metric_map") or {}
    ticker = _extract_question_ticker(question) or _extract_ticker(snapshot) or str(snapshot.get("page_title", "")).strip() or "ativo não identificado"
    summary = str(snapshot.get("summary", "")).strip() or "sem resumo salvo"
    lines = [str(item).strip() for item in (snapshot.get("lines") or []) if str(item).strip()][:12]
    metrics = "; ".join(f"{key}: {value}" for key, value in metric_map.items() if value) or "nenhuma métrica estruturada"
    strategy = get_asset_strategy(ticker)
    fundamentals = _asset_fundamentals(snapshot).get(ticker, {})
    strategy_context = []
    if strategy.get("price_ceiling") is not None:
        strategy_context.append(f"preço-teto: {_format_brl(strategy['price_ceiling'])}")
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


def _ask_grounded_asset_news(question: str, ticker: str, snapshot: dict) -> str | None:
    if not GEMINI_API_KEY:
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


def _asset_news_answer(question: str, ticker: str, snapshot: dict, fundamentals: dict | None = None) -> str | None:
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

    grounded_news = _ask_grounded_asset_news(question, ticker, snapshot)
    if grounded_news:
        return grounded_news
    return None


def save_investment_snapshot(
    summary: str,
    metrics: list[str] | None = None,
    lines: list[str] | None = None,
    page_url: str = "",
    page_title: str = "",
    extra: dict | None = None,
):
    payload = {
        "updated_at": time.time(),
        "summary": re.sub(r"\s+", " ", str(summary or "")).strip(),
        "metrics": [re.sub(r"\s+", " ", str(item or "")).strip() for item in list(metrics or []) if str(item or "").strip()],
        "lines": [re.sub(r"\s+", " ", str(item or "")).strip() for item in list(lines or [])[:30] if str(item or "").strip()],
        "page_url": str(page_url or "").strip(),
        "page_title": str(page_title or "").strip(),
    }
    if isinstance(extra, dict):
        payload.update(extra)
    if not isinstance(payload.get("metric_map"), dict):
        payload["metric_map"] = _extract_metric_map(payload.get("metrics"), payload.get("lines"))

    current = _load_json(INVESTMENT_SNAPSHOT_PATH)
    if isinstance(current, dict):
        current_positions = current.get("asset_positions")
        new_positions = payload.get("asset_positions")
        if isinstance(current_positions, dict) and isinstance(new_positions, dict):
            current_count = len(current_positions)
            new_count = len(new_positions)
            unresolved = payload.get("unresolved_category_counts")
            looks_partial = bool(unresolved) or new_count < current_count
            if current_count > new_count and looks_partial:
                merged_positions = dict(current_positions)
                merged_positions.update(new_positions)
                payload["asset_positions"] = merged_positions

                for key in ("asset_fundamentals", "asset_dividend_events"):
                    old_map = current.get(key)
                    new_map = payload.get(key)
                    if isinstance(old_map, dict) and isinstance(new_map, dict):
                        merged_map = dict(old_map)
                        merged_map.update(new_map)
                        payload[key] = merged_map

                payload["partial_capture_merged"] = True
                payload["partial_capture_note"] = (
                    f"Atualização parcial preservou {current_count} posições anteriores "
                    f"e atualizou {new_count} posições capturadas agora."
                )
    _save_json(INVESTMENT_SNAPSHOT_PATH, payload)
    sync_portfolio_snapshot_note(payload)
    return payload


def load_investment_snapshot() -> dict:
    data = _load_json(INVESTMENT_SNAPSHOT_PATH)
    return data if isinstance(data, dict) else {}


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


def format_investment_financial_report() -> str:
    snapshot = load_investment_snapshot()
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

    breakdown = _category_breakdown(snapshot)
    if breakdown:
        allocation = "; ".join(f"{category} {value}" for category, value in list(breakdown.items())[:3] if value)
        if allocation:
            report_parts.append("Alocação atual: " + allocation + ".")

    attention_items = _portfolio_attention_items(snapshot)[:2]
    if attention_items:
        attention_parts = []
        for item in attention_items:
            reason_text = ", ".join(item.get("reasons", [])[:1])
            opinion = ""
            opinions = item.get("opinions") or []
            if opinions:
                opinion = str(opinions[0]).strip()
            attention_parts.append(f"{item['ticker']}: {reason_text}")
        attention_parts = _filter_new_signal_texts("attention", attention_parts, only_new=True, mark_seen=True)
        attention_parts = attention_parts[:2]
    else:
        attention_parts = []
    if attention_parts:
        report_parts.append("Atenção: " + "; ".join(attention_parts) + ".")

    ceiling_items = _material_price_ceiling_items(_portfolio_items_above_ceiling(snapshot), threshold_percent=2.0)[:2]
    if ceiling_items:
        ceiling_parts = []
        for item in ceiling_items:
            premium = _format_percent(item.get("premium_percent"), digits=1)
            ceiling_parts.append(
                f"{item['ticker']} acima do teto em {premium}"
                if premium
                else f"{item['ticker']} acima do teto"
            )
    else:
        ceiling_parts = []
    if ceiling_parts:
        report_parts.append("Preço-teto: " + "; ".join(ceiling_parts) + ".")

    vacancy_parts = _filter_new_signal_texts(
        "vacancy",
        _vacancy_alert_items(snapshot),
        only_new=True,
        mark_seen=True,
    )[:2]
    if vacancy_parts:
        report_parts.append("VacÃ¢ncia: " + "; ".join(vacancy_parts) + ".")

    volatility_parts = _filter_new_signal_texts(
        "volatility",
        _volatility_alert_items(snapshot),
        only_new=True,
        mark_seen=True,
    )[:2]
    if volatility_parts:
        report_parts.append("Volatilidade: " + "; ".join(volatility_parts) + ".")

    dividend_events = _portfolio_dividend_schedule(snapshot, limit=1)
    if dividend_events:
        dividend_parts = [_format_dividend_event_brief(item["ticker"], item["event"]) for item in dividend_events]
        dividend_parts = _filter_new_signal_texts("dividend", dividend_parts, only_new=True, mark_seen=True)
        if dividend_parts:
            report_parts.append("Próximo dividendo no radar: " + "; ".join(dividend_parts[:1]) + ".")

    news_items = _portfolio_news_digest(snapshot, limit_assets=5, limit_summaries=1, only_new=True, mark_seen=True)
    if news_items:
        compact_news = _compact_report_news(news_items[0])
        if compact_news:
            report_parts.append("Notícia nova relevante: " + compact_news)

    if attention_parts or ceiling_parts or vacancy_parts or volatility_parts:
        report_parts.append(
            "Leitura geral: revisar antes de aumentar posição."
        )
    else:
        report_parts.append(
            "Leitura geral: sem alerta crítico novo salvo agora."
        )

    return "Relatório financeiro. " + " ".join(part for part in report_parts if part)


def answer_investment_snapshot_question(question: str) -> str:
    snapshot = load_investment_snapshot()
    updated_at = float(snapshot.get("updated_at") or 0)
    summary = str(snapshot.get("summary", "")).strip()
    metric_map = snapshot.get("metric_map") or {}
    normalized = _normalize(question)
    question_ticker = _extract_question_ticker(question)
    strategy = get_asset_strategy(question_ticker) if question_ticker else {}
    asset_positions = _asset_positions(snapshot)
    asset_position = asset_positions.get(question_ticker, {}) if question_ticker else {}

    if question_ticker and _looks_like_broader_investment_question(normalized) and asset_position:
        return _format_position_reading(snapshot, question_ticker, asset_position)

    if question_ticker and _mentions_price_ceiling(normalized):
        current_price = _parse_currency_value(asset_position.get("current_price")) if asset_position else _extract_current_price(snapshot)
        effective_ceiling, source = _effective_price_ceiling(snapshot, question_ticker, asset_position or {})
        ceiling = strategy.get("price_ceiling")
        if ceiling is not None:
            if current_price is not None:
                relation = "abaixo" if current_price <= float(ceiling) else "acima"
                return (
                    f"Seu preço-teto salvo para {question_ticker} é {_format_brl(float(ceiling))}. "
                    f"Pela cotação visível, ele está {relation} desse nível."
                )
            return (
                f"Seu preço-teto salvo para {question_ticker} é {_format_brl(float(ceiling))}. "
                "Ainda não consegui comparar isso com a cotação atual visível."
            )
        return f"Ainda não tenho preço-teto salvo para {question_ticker}."

    if "margem de segurança" in normalized or "margem de seguranca" in normalized:
        settings = get_auto_ceiling_settings()
        return (
            f"Sua base automática está em yield alvo de {str(settings['target_yield_percent']).replace('.', ',')}%. "
            f"Enquanto faltarem dividendos anuais confiáveis por ativo, o fallback local usa "
            f"{str(settings['margin_percent']).replace('.', ',')}% sobre {('preço médio' if settings['reference'] == 'preco_medio' else 'cotação atual')}."
        )

    if question_ticker and "watchlist" in normalized:
        return (
            f"{question_ticker} já está na sua watchlist."
            if strategy.get("in_watchlist")
            else f"{question_ticker} não está na sua watchlist."
        )

    if question_ticker and "tese" in normalized:
        thesis = str(strategy.get("thesis", "")).strip()
        if thesis:
            return f"Sua tese salva para {question_ticker} é: {thesis}"
        return f"Ainda não tenho tese salva para {question_ticker}."

    if question_ticker and asset_positions and not asset_position:
        return (
            f"Na sua carteira atualizada, eu não encontrei {question_ticker}. "
            f"Ela foi atualizada {_format_timestamp_natural(updated_at)}."
        )

    if not updated_at and not summary:
        return "Ainda não tenho dados locais da sua carteira. Peça para abrir ou atualizar o Investidor10 primeiro."

    if any(token in normalized for token in ("quando", "atualizado", "atualizacao", "salvo", "snapshot")):
        return f"Sua carteira está atualizada {_format_timestamp_natural(updated_at)}."

    if question_ticker and any(term in normalized for term in {"caro", "barato", "criterio", "critério"}):
        if asset_position:
            current_price = _parse_currency_value(asset_position.get("current_price"))
            ceiling, source = _effective_price_ceiling(snapshot, question_ticker, asset_position)
            if current_price is not None and ceiling is not None:
                criterion_name = "seu preço-teto" if source == "manual" else "o preço-teto automático"
                if current_price > ceiling:
                    distance_percent = ((current_price / ceiling) - 1.0) * 100.0 if ceiling > 0 else 0.0
                    return (
                        f"Para o seu critério atual, {question_ticker} parece caro. "
                        f"Ele está em {_format_brl(current_price)}, cerca de {_format_percent(distance_percent)} acima de {criterion_name}, "
                        f"que hoje fica em {_format_brl(ceiling)}."
                    )
                return (
                    f"Para o seu critério atual, {question_ticker} não parece caro. "
                    f"Ele está em {_format_brl(current_price)}, abaixo de {criterion_name}, "
                    f"que hoje fica em {_format_brl(ceiling)}."
                )
        return f"Eu ainda não tenho base suficiente para dizer se {question_ticker} está caro para o seu critério."

    if "quais ativos" in normalized and ("acima do meu preco teto" in normalized or "acima do meu preço teto" in normalized):
        items = _portfolio_items_above_ceiling(snapshot)
        if not items:
            return "Nenhum ativo com preço-teto definido está acima do seu critério no snapshot atual."
        parts = []
        for item in items[:6]:
            premium = _format_percent(item.get("premium_percent"))
            parts.append(
                f"{item['ticker']} em {_format_brl(item['current_price'])}, acima do teto manual de {_format_brl(item['ceiling'])} por cerca de {premium}"
            )
        return "Ativos acima do seu preço-teto no snapshot atual: " + "; ".join(parts) + "."

    if "quais ativos" in normalized and "negativos" in normalized:
        negatives = []
        for ticker, position in _asset_positions(snapshot).items():
            rentability = _parse_percent_value(position.get("rentability"))
            if rentability is not None and rentability < 0:
                negatives.append((ticker, position.get("rentability", "")))
        if not negatives:
            return "No snapshot atual, eu não encontrei ativos com rentabilidade negativa."
        return "Ativos com rentabilidade negativa agora: " + "; ".join(f"{ticker} em {value}" for ticker, value in negatives) + "."

    if "merecem atencao" in normalized or "merecem atenção" in normalized:
        items = _portfolio_attention_items(snapshot)
        if not items:
            return "No snapshot atual, eu não vi nenhuma posição gritando por atenção imediata."
        parts = []
        for item in items[:6]:
            reason_text = ", ".join(item["reasons"][:2])
            opinion_text = ""
            if item.get("opinions"):
                opinion_text = str(item["opinions"][0]).strip().rstrip(".")
            stance_text = _position_action_stance(snapshot, item["ticker"], _asset_positions(snapshot).get(item["ticker"], {})).strip().rstrip(".")
            extra = f" Cotação: {item['current_price']}." if item.get("current_price") else ""
            if opinion_text:
                parts.append(f"{item['ticker']}: {reason_text}. Minha leitura: {opinion_text}. Direção prática: {stance_text}.{extra}".strip())
            else:
                parts.append(f"{item['ticker']}: {reason_text}. Direção prática: {stance_text}.{extra}".strip())
        return "As posições que mais pedem atenção agora são: " + " ".join(parts)

    question_map = {
        "patrimonio": ("patrimonio", "patrimônio"),
        "valor investido": ("valor investido", "quanto investi", "tenho investido"),
        "valor atual": ("valor atual", "quanto vale", "valor da carteira"),
        "rentabilidade": ("rentabilidade", "rendeu", "retorno"),
        "proventos": ("proventos", "dividendos"),
        "saldo": ("saldo",),
        "lucro": ("lucro",),
        "prejuizo": ("prejuizo", "prejuízo"),
        "aporte": ("aporte", "aportes"),
        "preco medio": ("preco medio", "preço médio", "preço medio"),
        "cotacao": ("cotacao", "cotação"),
        "variacao": ("variacao", "variação", "subiu", "caiu"),
    }

    for canonical, hints in question_map.items():
        if any(hint in normalized for hint in hints):
            if asset_position:
                asset_value_map = {
                    "valor atual": asset_position.get("balance"),
                    "rentabilidade": asset_position.get("rentability"),
                    "preco medio": asset_position.get("average_price"),
                    "cotacao": asset_position.get("current_price"),
                    "variacao": asset_position.get("variation"),
                    "saldo": asset_position.get("balance"),
                }
                asset_value = asset_value_map.get(canonical)
                if asset_value:
                    return f"{question_ticker} está com {canonical} em {asset_value}. Carteira atualizada."
            value = metric_map.get(canonical)
            if value:
                return f"{canonical.capitalize()} em {value}. Carteira atualizada."
            if canonical == "patrimonio" and metric_map.get("valor atual"):
                return f"Não encontrei patrimônio explícito no recorte salvo, mas o valor atual está em {metric_map['valor atual']}. Carteira atualizada."
            break

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


_answer_investment_snapshot_question_base = answer_investment_snapshot_question


def answer_investment_snapshot_question(question: str) -> str:
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
        if question_ticker:
            events = _ticker_dividend_events(snapshot, question_ticker)
            if events:
                details = "; ".join(_format_dividend_event(question_ticker, event) for event in events[:3])
                return f"Os proximos eventos de dividendos que encontrei para {question_ticker} sao: {details}."
            dy_current = str(fundamentals.get("dividend_yield_current") or "").strip()
            if dy_current:
                return (
                    f"Ainda não encontrei uma próxima data de dividendo confiável para {question_ticker}. "
                    f"O que eu já tenho salvo é um dividend yield atual de {dy_current}."
                )
            return f"Ainda nao encontrei uma agenda de dividendos confiavel para {question_ticker}."
        return _portfolio_dividend_schedule_answer(snapshot)

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
        news_items = _portfolio_news_digest(
            snapshot,
            limit_assets=5,
            limit_summaries=3,
            only_new=True,
            mark_seen=True,
        )
        if news_items:
            return "Noticias novas que parecem mais uteis na carteira agora: " + " ".join(news_items)
        return "No momento, eu nao encontrei noticia nova, confiavel e especifica o bastante para a carteira."

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
        current_dy = fundamentals.get("dividend_yield_current")
        average_dy = fundamentals.get("dividend_yield_5y_average")
        if current_dy and average_dy:
            return f"O DY atual de {question_ticker} está em {current_dy}, com média de 5 anos em {average_dy}."
        if current_dy:
            return f"O DY atual de {question_ticker} está em {current_dy}."
        return f"Ainda não tenho DY salvo para {question_ticker}."

    if question_ticker and _contains_investment_phrase(normalized, "cotacao", "cotação", "cotaçao"):
        current_price = asset_position.get("current_price") or fundamentals.get("quote")
        if current_price:
            rentability = asset_position.get("rentability")
            if rentability:
                return f"A cotação de {question_ticker} está em {current_price}. Sua rentabilidade está em {rentability}."
            return f"A cotação de {question_ticker} está em {current_price}."
        return f"Ainda não tenho cotação salva para {question_ticker}."

    if question_ticker and _contains_investment_phrase(normalized, "preco medio", "preço medio", "preço médio", "preco médio"):
        average_price = asset_position.get("average_price")
        if average_price:
            return f"O preço médio de {question_ticker} está em {average_price}."
        return f"Ainda não tenho preço médio salvo para {question_ticker}."

    if question_ticker and _contains_investment_phrase(normalized, "variacao do dia", "variação do dia", "variacao hoje", "variação hoje", "no dia", "hoje"):
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

    if question_ticker and _contains_investment_phrase(normalized, "subindo", "caindo", "variacao", "variação", "alta", "queda"):
        variation = asset_position.get("variation")
        rentability = asset_position.get("rentability")
        if variation:
            variation_value = _parse_percent_value(variation)
            if variation_value is not None:
                if variation_value > 0:
                    response = f"No snapshot atual da posição, {question_ticker} aparece em alta, com variação de {variation}."
                    if rentability:
                        response += f" Desde o seu preço médio, a rentabilidade está em {rentability}."
                    return response
                if variation_value < 0:
                    response = f"No snapshot atual da posição, {question_ticker} aparece em queda, com variação de {variation}."
                    if rentability:
                        response += f" Desde o seu preço médio, a rentabilidade está em {rentability}."
                    return response
                response = f"No snapshot atual da posição, {question_ticker} aparece estável, com variação de {variation}."
                if rentability:
                    response += f" Desde o seu preço médio, a rentabilidade está em {rentability}."
                return response
            return f"A variação visível de {question_ticker} está em {variation}."
        return f"Ainda não tenho variação salva para {question_ticker}."

    if question_ticker and _contains_investment_phrase(normalized, "dividendos agendados", "proventos agendados", "dividendos previstos", "dividendos programados", "proximo dividendo", "próximo dividendo", "data ex", "data com"):
        return f"Ainda não tenho agenda de dividendos integrada para {question_ticker}. Hoje eu consigo ler proventos e DY salvos, mas não a próxima data com confiança."

    if question_ticker and _contains_investment_phrase(normalized, "fato relevante", "noticia", "notícias", "noticias", "relevante", "novidade"):
        news_answer = _asset_news_answer(question, question_ticker, snapshot, fundamentals)
        if news_answer:
            return news_answer
        return f"Ainda não consegui buscar notícias ou fatos relevantes confiáveis para {question_ticker}."

    if question_ticker and _mentions_price_ceiling(normalized):
        current_price = _parse_currency_value(asset_position.get("current_price")) if asset_position else _extract_current_price(snapshot)
        manual_ceiling = strategy.get("price_ceiling")
        effective_ceiling, source = _effective_price_ceiling(snapshot, question_ticker, asset_position or {})

        if manual_ceiling is None and effective_ceiling is not None:
            relation = ""
            if current_price is not None:
                relation = "abaixo" if current_price <= effective_ceiling else "acima"
            if source == "automatic_yield":
                prefix = (
                    f"Ainda não tenho preço-teto manual salvo para {question_ticker}. "
                    f"Pela sua base automática de yield alvo, o teto estimado fica em {_format_brl(effective_ceiling)}."
                )
            else:
                prefix = (
                    f"Ainda não tenho preço-teto manual salvo para {question_ticker}. "
                    f"Pela sua base automática atual, o teto estimado fica em {_format_brl(effective_ceiling)}."
                )
            if relation:
                return prefix + f" Na cotação visível, ele está {relation} desse nível."
            return prefix

    if "quais ativos" in normalized and ("acima do meu preco teto" in normalized or "acima do meu preço teto" in normalized):
        items = _portfolio_items_above_ceiling(snapshot)
        if not items:
            return "Nenhum ativo com preço-teto manual ou automático está acima do seu critério no snapshot atual."
        parts = []
        for item in items[:6]:
            source_label = "teto manual"
            if item.get("source") == "automatic_yield":
                source_label = "teto automático por yield"
            elif item.get("source") == "automatic":
                source_label = "teto automático"
            premium = _format_percent(item.get("premium_percent"))
            parts.append(
                f"{item['ticker']} em {_format_brl(item['current_price'])}, acima do {source_label} de {_format_brl(item['ceiling'])} por cerca de {premium}"
            )
        return "Ativos acima do seu preço-teto no snapshot atual: " + "; ".join(parts) + "."

    if question_ticker and _contains_investment_phrase(normalized, "dividendos agendados", "proventos agendados", "dividendos previstos", "dividendos programados", "proximo dividendo", "data ex", "data com"):
        events = _ticker_dividend_events(snapshot, question_ticker)
        if events:
            details = "; ".join(_format_dividend_event(question_ticker, event) for event in events[:3])
            return f"Os proximos eventos de dividendos que encontrei para {question_ticker} sao: {details}."
        return f"Ainda nao encontrei uma agenda de dividendos confiavel para {question_ticker}."

    return _answer_investment_snapshot_question_base(question)
