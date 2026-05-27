import re
import json
import threading
import time
from pathlib import Path

from config import INVESTIDOR10_PRIVATE_WALLET_URL, INVESTIDOR10_WALLET_URL, INVESTMENT_BACKGROUND_REFRESH_ENABLED
from core.cache_policy import INVESTMENT_REPORT_CACHE_POLICY, INVESTMENT_SUMMARY_CACHE_POLICY, is_cache_fresh
from memory.investment_snapshot import (
    answer_investment_snapshot_question,
    format_investment_financial_report,
    format_investment_snapshot_summary,
    load_investment_snapshot,
)
from memory.investment_strategy import (
    add_to_watchlist,
    format_auto_ceiling_settings,
    format_watchlist,
    remove_from_watchlist,
    set_asset_thesis,
    set_auto_ceiling_margin,
    set_price_ceiling,
)
from memory.public_wallet_refresh import (
    format_public_wallet_refresh_result,
    is_wallet_snapshot_stale,
    refresh_wallet_snapshot_auto,
    refresh_wallet_snapshot_if_stale,
)

INVESTMENT_MODE_REFRESH_SECONDS = 6 * 60 * 60
ASSET_FOCUS_REFRESH_SECONDS = 2 * 60 * 60
BACKGROUND_REFRESH_SECONDS = 15 * 60 * 60
BACKGROUND_REFRESH_POLL_SECONDS = 10 * 60
INVESTMENT_SUMMARY_CACHE_PATH = INVESTMENT_SUMMARY_CACHE_POLICY.path
INVESTMENT_REPORT_CACHE_PATH = INVESTMENT_REPORT_CACHE_POLICY.path
DEFAULT_INVESTMENT_CACHE_TTL_SECONDS = INVESTMENT_SUMMARY_CACHE_POLICY.ttl_seconds
_BACKGROUND_REFRESH_STARTED = False
_BACKGROUND_REFRESH_LOCK = threading.Lock()


def _read_text_cache(path: Path, ttl_seconds: int) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    created_at = payload.get("created_at")
    text = str(payload.get("text") or "").strip()
    if not isinstance(created_at, (int, float)) or not text:
        return None
    if not is_cache_fresh(created_at, ttl_seconds, now=time.time()):
        return None
    return text


def _write_text_cache(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"created_at": time.time(), "text": str(text or "")}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception:
        pass


def _clear_investment_caches() -> None:
    for path in (INVESTMENT_SUMMARY_CACHE_PATH, INVESTMENT_REPORT_CACHE_PATH):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass


def _extract_ticker(question: str) -> str:
    text = str(question or "")
    match = re.search(r"\b([A-Za-z]{4,5}\d{1,2})\b", text)
    if match:
        return match.group(1).upper()
    for symbol in ("BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOGE"):
        if re.search(rf"\b{symbol}(?:[-/](?:BRL|USD|USDT))?\b", text, flags=re.I):
            return symbol
    return ""


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
        _clear_investment_caches()
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
            refreshed = refresh_wallet_snapshot_auto(force=True)
            _clear_investment_caches()
            return refreshed
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
            _clear_investment_caches()
            _run_background_portfolio_monitor()
            return refreshed
    except Exception:
        pass

    refreshed = _try_visible_wallet_refresh()
    _run_background_portfolio_monitor()
    return refreshed


def _run_background_portfolio_monitor() -> None:
    try:
        from services.investment_monitor_service import run_portfolio_monitor_once

        run_portfolio_monitor_once(notify=True)
    except Exception:
        pass


def _background_refresh_worker():
    _background_refresh_once()
    while True:
        time.sleep(BACKGROUND_REFRESH_POLL_SECONDS)
        _background_refresh_once()


def start_background_investment_refresh_loop() -> bool:
    global _BACKGROUND_REFRESH_STARTED
    if not INVESTMENT_BACKGROUND_REFRESH_ENABLED:
        return False
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


def investment_background_refresh_status() -> dict:
    return {
        "enabled": bool(INVESTMENT_BACKGROUND_REFRESH_ENABLED),
        "started": bool(_BACKGROUND_REFRESH_STARTED),
        "poll_seconds": BACKGROUND_REFRESH_POLL_SECONDS,
        "stale_after_seconds": BACKGROUND_REFRESH_SECONDS,
    }


def _build_investment_memory_summary() -> str:
    _ensure_investment_snapshot_for_mode()
    return format_investment_snapshot_summary()


def investment_memory_summary(*, use_cache: bool = True, ttl_seconds: int = DEFAULT_INVESTMENT_CACHE_TTL_SECONDS):
    if use_cache:
        cached = _read_text_cache(INVESTMENT_SUMMARY_CACHE_PATH, ttl_seconds)
        if cached:
            return cached

    summary = _build_investment_memory_summary()
    if use_cache:
        _write_text_cache(INVESTMENT_SUMMARY_CACHE_PATH, summary)
    return summary


def _build_investment_financial_report() -> str:
    _ensure_investment_snapshot_for_mode()
    return format_investment_financial_report()


def investment_financial_report(*, use_cache: bool = True, ttl_seconds: int = DEFAULT_INVESTMENT_CACHE_TTL_SECONDS):
    if use_cache:
        cached = _read_text_cache(INVESTMENT_REPORT_CACHE_PATH, ttl_seconds)
        if cached:
            return cached

    report = _build_investment_financial_report()
    if use_cache:
        _write_text_cache(INVESTMENT_REPORT_CACHE_PATH, report)
    return report


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
        _clear_investment_caches()
        summary = str(snapshot.get("summary", "")).strip()
        return summary or format_public_wallet_refresh_result(force=True)
    except Exception:
        result = format_public_wallet_refresh_result(force=True)
        _clear_investment_caches()
        return result


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
