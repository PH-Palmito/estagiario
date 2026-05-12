import threading
import re
import time

from memory.investment_snapshot import (
    answer_investment_snapshot_question,
    format_investment_financial_report,
    format_investment_snapshot_summary,
    load_investment_snapshot,
)
from memory.investment_strategy import (
    add_to_watchlist,
    format_watchlist,
    format_auto_ceiling_settings,
    remove_from_watchlist,
    set_auto_ceiling_margin,
    set_asset_thesis,
    set_price_ceiling,
)
from memory.public_wallet_refresh import (
    format_public_wallet_refresh_result,
    is_wallet_snapshot_stale,
    refresh_wallet_snapshot_auto,
    refresh_wallet_snapshot_if_stale,
)
from config import INVESTIDOR10_PRIVATE_WALLET_URL, INVESTIDOR10_WALLET_URL

INVESTMENT_MODE_REFRESH_SECONDS = 6 * 60 * 60
ASSET_FOCUS_REFRESH_SECONDS = 2 * 60 * 60
BACKGROUND_REFRESH_SECONDS = 15 * 60 * 60
BACKGROUND_REFRESH_POLL_SECONDS = 10 * 60
_BACKGROUND_REFRESH_STARTED = False
_BACKGROUND_REFRESH_LOCK = threading.Lock()


def _extract_ticker(question: str) -> str:
    match = re.search(r"\b([A-Za-z]{3,5}\d{0,2})(?:[-/](?:BRL|USD|USDT))?\b", str(question or ""))
    return match.group(1).upper() if match else ""


def _ensure_investment_snapshot_for_mode() -> dict:
    current = load_investment_snapshot()
    if not is_wallet_snapshot_stale(current, max_age_seconds=INVESTMENT_MODE_REFRESH_SECONDS):
        return current
    return _background_refresh_once()


def _try_visible_wallet_refresh() -> dict:
    wallet_url = str(INVESTIDOR10_PRIVATE_WALLET_URL or INVESTIDOR10_WALLET_URL or "").strip()
    if not wallet_url:
        return load_investment_snapshot()

    try:
        from tools.browser_tools import _visible_wallet_capture_summary

        _visible_wallet_capture_summary(wallet_url, close_tab=True)
    except Exception:
        pass

    return load_investment_snapshot()


def _ensure_investment_snapshot_for_question(question: str) -> dict:
    ticker = _extract_ticker(question)
    snapshot = load_investment_snapshot()

    if not ticker:
        return _ensure_investment_snapshot_for_mode()

    positions = snapshot.get("asset_positions") or {}
    fundamentals = snapshot.get("asset_fundamentals") or {}
    missing_asset_context = ticker not in positions or ticker not in fundamentals

    if missing_asset_context or is_wallet_snapshot_stale(snapshot, max_age_seconds=ASSET_FOCUS_REFRESH_SECONDS):
        try:
            return refresh_wallet_snapshot_auto(force=True)
        except Exception:
            refreshed = _try_visible_wallet_refresh()
            if refreshed.get("updated_at") and not is_wallet_snapshot_stale(
                refreshed,
                max_age_seconds=ASSET_FOCUS_REFRESH_SECONDS,
            ):
                return refreshed
            return refresh_wallet_snapshot_if_stale(max_age_seconds=ASSET_FOCUS_REFRESH_SECONDS)

    return snapshot


def _background_refresh_once() -> dict:
    current = load_investment_snapshot()
    if not is_wallet_snapshot_stale(current, max_age_seconds=BACKGROUND_REFRESH_SECONDS):
        return current

    try:
        refreshed = refresh_wallet_snapshot_auto(force=True)
        if not is_wallet_snapshot_stale(refreshed, max_age_seconds=BACKGROUND_REFRESH_SECONDS):
            return refreshed
    except Exception:
        pass

    return _try_visible_wallet_refresh()


def _background_refresh_worker():
    _background_refresh_once()
    while True:
        time.sleep(BACKGROUND_REFRESH_POLL_SECONDS)
        _background_refresh_once()


def start_background_investment_refresh_loop() -> bool:
    global _BACKGROUND_REFRESH_STARTED
    with _BACKGROUND_REFRESH_LOCK:
        if _BACKGROUND_REFRESH_STARTED:
            return False
        threading.Thread(
            target=_background_refresh_worker,
            name="axel-investment-refresh",
            daemon=True,
        ).start()
        _BACKGROUND_REFRESH_STARTED = True
        return True


def investment_memory_summary():
    _ensure_investment_snapshot_for_mode()
    return format_investment_snapshot_summary()


def investment_financial_report():
    _ensure_investment_snapshot_for_mode()
    return format_investment_financial_report()


def investment_memory_answer(question: str):
    _ensure_investment_snapshot_for_question(question)
    return answer_investment_snapshot_question(question)


def investment_memory_status():
    _ensure_investment_snapshot_for_mode()
    snapshot = load_investment_snapshot()
    if snapshot.get("updated_at"):
        if str(snapshot.get("source", "")).strip() == "investidor10_public_wallet":
            return "Memória local da carteira pública disponível."
        return "Memória local de investimentos disponível."
    return "Ainda não há memória local de investimentos salva."


def investment_refresh_public_wallet():
    try:
        snapshot = refresh_wallet_snapshot_auto(force=True)
        summary = str(snapshot.get("summary", "")).strip()
        return summary or format_public_wallet_refresh_result(force=True)
    except Exception:
        return format_public_wallet_refresh_result(force=True)


def investment_set_price_ceiling(ticker: str, price: str):
    return set_price_ceiling(ticker, price)


def investment_set_auto_ceiling_margin(value: str):
    return set_auto_ceiling_margin(value)


def investment_get_auto_ceiling_settings():
    return format_auto_ceiling_settings()


def investment_add_watchlist(ticker: str):
    return add_to_watchlist(ticker)


def investment_remove_watchlist(ticker: str):
    return remove_from_watchlist(ticker)


def investment_list_watchlist():
    return format_watchlist()


def investment_set_thesis(ticker: str, thesis: str):
    return set_asset_thesis(ticker, thesis)
