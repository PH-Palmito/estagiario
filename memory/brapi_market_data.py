import time
from datetime import datetime, timezone

import requests

from config import BRAPI_ENABLED, BRAPI_TOKEN


BRAPI_QUOTE_URL = "https://brapi.dev/api/quote/{ticker}"
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36"
    )
}


def _http_get(url: str, params: dict | None = None) -> requests.Response:
    session = requests.Session()
    session.trust_env = False
    headers = dict(REQUEST_HEADERS)
    if BRAPI_TOKEN:
        headers["Authorization"] = f"Bearer {BRAPI_TOKEN}"
    return session.get(url, headers=headers, params=params or {}, timeout=20)


def _parse_brapi_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _extract_next_dividend_events(item: dict) -> list[dict]:
    dividends_data = item.get("dividendsData") or {}
    cash_dividends = dividends_data.get("cashDividends") or []
    now = datetime.now(timezone.utc)
    events = []

    for raw in cash_dividends:
        payment_dt = _parse_brapi_datetime(raw.get("paymentDate"))
        last_prior_dt = _parse_brapi_datetime(raw.get("lastDatePrior"))
        approved_dt = _parse_brapi_datetime(raw.get("approvedOn"))
        if not payment_dt and not last_prior_dt:
            continue

        anchor = payment_dt or last_prior_dt
        if anchor and anchor < now:
            continue

        rate = raw.get("rate")
        try:
            rate_value = float(rate) if rate is not None else None
        except Exception:
            rate_value = None

        if rate_value is not None and rate_value > 1000:
            rate_value = rate_value / 1_000_000

        events.append(
            {
                "label": str(raw.get("label") or "").strip() or "Provento",
                "payment_date": payment_dt.isoformat() if payment_dt else "",
                "last_date_prior": last_prior_dt.isoformat() if last_prior_dt else "",
                "approved_on": approved_dt.isoformat() if approved_dt else "",
                "rate": rate_value,
            }
        )

    def sort_key(event: dict):
        return (
            _parse_brapi_datetime(event.get("last_date_prior")) or _parse_brapi_datetime(event.get("payment_date")) or now,
            _parse_brapi_datetime(event.get("payment_date")) or now,
        )

    events.sort(key=sort_key)
    return events[:6]


def fetch_brapi_asset_data(ticker: str) -> dict:
    if not BRAPI_ENABLED:
        raise RuntimeError("BRAPI desativada.")

    normalized = str(ticker or "").strip().upper()
    if not normalized:
        raise RuntimeError("Ticker inválido.")

    response = _http_get(
        BRAPI_QUOTE_URL.format(ticker=normalized),
        params={
            "fundamental": "true",
            "dividends": "true",
        },
    )
    response.raise_for_status()
    data = response.json()
    results = data.get("results") or []
    if not results:
        raise RuntimeError("BRAPI sem resultados para o ticker.")

    item = results[0] or {}
    regular_market_price = item.get("regularMarketPrice")
    regular_market_change_percent = item.get("regularMarketChangePercent")
    regular_market_change = item.get("regularMarketChange")
    regular_market_time = str(item.get("regularMarketTime") or "").strip()
    long_name = str(item.get("longName") or item.get("shortName") or "").strip()

    quote = ""
    if isinstance(regular_market_price, (int, float)):
        quote = "R$ " + f"{float(regular_market_price):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    dy_current_percent = item.get("dividendYield")
    dy_current = ""
    if isinstance(dy_current_percent, (int, float)):
        dy_current = f"{float(dy_current_percent):.2f}%".replace(".", ",")

    return {
        "ticker": normalized,
        "company_name": long_name,
        "quote": quote,
        "quote_value": float(regular_market_price) if isinstance(regular_market_price, (int, float)) else None,
        "dividend_yield_current": dy_current,
        "dividend_yield_current_percent": float(dy_current_percent) if isinstance(dy_current_percent, (int, float)) else None,
        "dividend_yield_5y_average": "",
        "dividend_yield_5y_average_percent": None,
        "p_l": str(item.get("priceEarnings") or "").strip(),
        "p_vp": str(item.get("priceToBook") or "").strip(),
        "annual_dividend_estimate_per_share": None,
        "regular_market_change_percent": float(regular_market_change_percent) if isinstance(regular_market_change_percent, (int, float)) else None,
        "regular_market_change": float(regular_market_change) if isinstance(regular_market_change, (int, float)) else None,
        "regular_market_time": regular_market_time,
        "regular_market_previous_close": float(item.get("regularMarketPreviousClose")) if isinstance(item.get("regularMarketPreviousClose"), (int, float)) else None,
        "regular_market_day_high": float(item.get("regularMarketDayHigh")) if isinstance(item.get("regularMarketDayHigh"), (int, float)) else None,
        "regular_market_day_low": float(item.get("regularMarketDayLow")) if isinstance(item.get("regularMarketDayLow"), (int, float)) else None,
        "regular_market_volume": float(item.get("regularMarketVolume")) if isinstance(item.get("regularMarketVolume"), (int, float)) else None,
        "next_dividend_events": _extract_next_dividend_events(item),
        "source_url": BRAPI_QUOTE_URL.format(ticker=normalized),
        "source": "brapi",
        "updated_at": time.time(),
    }
