import re
import time
from html.parser import HTMLParser

import requests

from memory.brapi_market_data import fetch_brapi_asset_data

INVESTIDOR10_ASSET_URL_TEMPLATES = (
    "https://investidor10.com.br/acoes/{ticker}/",
    "https://investidor10.com.br/fiis/{ticker}/",
    "https://investidor10.com.br/etfs/{ticker}/",
    "https://investidor10.com.br/bdrs/{ticker}/",
)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0 Safari/537.36"
    )
}


def _http_get(url: str) -> requests.Response:
    session = requests.Session()
    session.trust_env = False
    return session.get(url, headers=REQUEST_HEADERS, timeout=20)


class _VisibleTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "noscript"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style", "noscript"} and self._skip_depth > 0:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = re.sub(r"\s+", " ", data or "").strip()
        if text:
            self.items.append(text)


def _extract_visible_items(html: str) -> list[str]:
    parser = _VisibleTextParser()
    parser.feed(html or "")
    return [str(item).strip() for item in parser.items if str(item).strip()]


def _first_value_after(items: list[str], labels: tuple[str, ...], pattern: str, window: int = 6) -> str:
    compiled = re.compile(pattern)
    for index, token in enumerate(items):
        if token not in labels:
            continue
        for offset in range(1, window + 1):
            target = index + offset
            if target >= len(items):
                break
            value = str(items[target]).strip()
            if compiled.fullmatch(value):
                return value
    return ""


def _first_value_after_contains(items: list[str], label_fragment: str, pattern: str, window: int = 6) -> str:
    compiled = re.compile(pattern)
    fragment = str(label_fragment or "").strip().lower()
    for index, token in enumerate(items):
        if fragment not in str(token or "").strip().lower():
            continue
        for offset in range(1, window + 1):
            target = index + offset
            if target >= len(items):
                break
            value = str(items[target]).strip()
            if compiled.fullmatch(value):
                return value
    return ""


def _extract_company_name(items: list[str], ticker: str) -> str:
    upper_ticker = ticker.upper()
    for index, token in enumerate(items):
        if token.strip().upper() == upper_ticker:
            for offset in range(1, 4):
                target = index + offset
                if target >= len(items):
                    break
                candidate = str(items[target]).strip()
                if candidate and candidate.upper() != upper_ticker and len(candidate) > 3:
                    return candidate
    return ""


def _parse_percent(value: str) -> float | None:
    text = str(value or "").strip().replace("%", "").replace(" ", "")
    if not text:
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _parse_currency(value: str) -> float | None:
    text = str(value or "").strip().lower().replace("r$", "").replace(" ", "")
    if not text:
        return None
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def fetch_asset_fundamentals(ticker: str) -> dict:
    normalized = str(ticker or "").strip().lower()
    if not re.fullmatch(r"[a-z]{4,5}\d{1,2}", normalized):
        raise RuntimeError("Ticker inválido para buscar fundamentos.")

    try:
        brapi_data = fetch_brapi_asset_data(normalized)
        if brapi_data.get("quote") or brapi_data.get("dividend_yield_current"):
            return brapi_data
    except Exception:
        pass

    url = ""
    items: list[str] = []
    for template in INVESTIDOR10_ASSET_URL_TEMPLATES:
        candidate_url = template.format(ticker=normalized)
        try:
            response = _http_get(candidate_url)
            response.raise_for_status()
            candidate_items = _extract_visible_items(response.text)
            if candidate_items:
                url = candidate_url
                items = candidate_items
                break
        except Exception:
            continue
    if not items:
        raise RuntimeError("Página do ativo sem conteúdo visível útil.")

    quote = _first_value_after(items, ("Cotação", "COTAÇÃO"), r"R\$\s*[-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2})")
    if not quote:
        quote = _first_value_after_contains(items, "cotação", r"R\$\s*[-+]?\d{1,3}(?:\.\d{3})*(?:,\d{2})")
    dy_current = _first_value_after(items, ("DY atual:", "Dividend Yield", "DY"), r"[-+]?\d+(?:,\d+)?%")
    dy_5y = _first_value_after(items, ("DY médio em 5 anos:",), r"[-+]?\d+(?:,\d+)?%")
    vacancy = _first_value_after_contains(items, "vac", r"[-+]?\d+(?:,\d+)?%")
    p_l = _first_value_after(items, ("P/L",), r"-?\d+(?:,\d+)?")
    p_vp = _first_value_after(items, ("P/VP",), r"-?\d+(?:,\d+)?")
    company_name = _extract_company_name(items, normalized)
    company_name_price = _parse_currency(company_name)
    if company_name_price is not None:
        quote = company_name
        company_name = ""

    quote_value = _parse_currency(quote)
    dy_current_percent = _parse_percent(dy_current)
    annual_dividend_estimate = None
    if quote_value is not None and dy_current_percent is not None:
        annual_dividend_estimate = quote_value * (dy_current_percent / 100.0)

    return {
        "ticker": normalized.upper(),
        "company_name": company_name,
        "quote": quote,
        "quote_value": quote_value,
        "dividend_yield_current": dy_current,
        "dividend_yield_current_percent": dy_current_percent,
        "dividend_yield_5y_average": dy_5y,
        "dividend_yield_5y_average_percent": _parse_percent(dy_5y),
        "vacancy": vacancy,
        "vacancy_percent": _parse_percent(vacancy),
        "p_l": p_l,
        "p_vp": p_vp,
        "annual_dividend_estimate_per_share": annual_dividend_estimate,
        "source_url": url,
        "updated_at": time.time(),
    }


def fetch_many_asset_fundamentals(tickers: list[str]) -> dict[str, dict]:
    results: dict[str, dict] = {}
    seen: set[str] = set()
    for raw_ticker in tickers:
        normalized = str(raw_ticker or "").strip().upper()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        try:
            results[normalized] = fetch_asset_fundamentals(normalized)
        except Exception:
            continue
    return results
