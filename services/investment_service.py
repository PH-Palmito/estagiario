from __future__ import annotations

from tools.investment_tools import (
    investment_add_watchlist as add_watchlist,
    investment_daily_change_report as daily_change_report,
    investment_financial_report as financial_report,
    investment_get_auto_ceiling_settings as get_auto_ceiling_settings,
    investment_list_watchlist as list_watchlist,
    investment_memory_answer as answer,
    investment_memory_status as status,
    investment_memory_summary as summary,
    investment_refresh_public_wallet as refresh_public_wallet,
    investment_remove_watchlist as remove_watchlist,
    investment_set_auto_ceiling_margin as set_auto_ceiling_margin,
    investment_set_price_ceiling as set_price_ceiling,
    investment_set_thesis as set_thesis,
)


def investment_summary() -> str:
    return summary()


def investment_report() -> str:
    return financial_report()


def investment_daily_report() -> str:
    return daily_change_report()


def investment_status() -> str:
    return status()


def investment_answer(question: str) -> str:
    return answer(question)


def investment_monitor() -> str:
    from services.investment_monitor_service import run_portfolio_monitor_once

    return run_portfolio_monitor_once(notify=False)
