from memory.investment_snapshot import (
    answer_investment_snapshot_question,
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
    refresh_public_wallet_snapshot_if_stale,
)


def investment_memory_summary():
    refresh_public_wallet_snapshot_if_stale()
    return format_investment_snapshot_summary()


def investment_memory_answer(question: str):
    refresh_public_wallet_snapshot_if_stale()
    return answer_investment_snapshot_question(question)


def investment_memory_status():
    refresh_public_wallet_snapshot_if_stale()
    snapshot = load_investment_snapshot()
    if snapshot.get("updated_at"):
        if str(snapshot.get("source", "")).strip() == "investidor10_public_wallet":
            return "Memória local da carteira pública disponível."
        return "Memória local de investimentos disponível."
    return "Ainda não há memória local de investimentos salva."


def investment_refresh_public_wallet():
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
