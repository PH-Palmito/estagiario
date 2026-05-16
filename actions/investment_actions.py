from __future__ import annotations

from actions.registry import ActionSpec, register_action
from tools.investment_tools import (
    investment_add_watchlist,
    investment_financial_report,
    investment_get_auto_ceiling_settings,
    investment_list_watchlist,
    investment_memory_answer,
    investment_memory_status,
    investment_memory_summary,
    investment_refresh_public_wallet,
    investment_remove_watchlist,
    investment_set_auto_ceiling_margin,
    investment_set_price_ceiling,
    investment_set_thesis,
)


def _register(
    name: str,
    description: str,
    handler,
    parameters: dict | None = None,
    read_only: bool = True,
    requires_confirmation: bool = False,
) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category="investments",
            read_only=read_only,
            requires_confirmation=requires_confirmation,
            parameters=parameters or {},
        )
    )


def register_investment_actions() -> None:
    question_param = {"question": {"type": "string", "description": "Pergunta sobre investimentos.", "required": True}}
    ticker_param = {"ticker": {"type": "string", "description": "Ticker do ativo.", "required": True}}
    _register("investment.summary", "Resume a memoria local da carteira.", lambda _args: investment_memory_summary())
    _register("investment.report", "Gera relatorio financeiro da carteira.", lambda _args: investment_financial_report())
    _register("investment.status", "Mostra status da memoria local de investimentos.", lambda _args: investment_memory_status())
    _register("investment.answer", "Responde pergunta usando memoria local e contexto de investimentos.", lambda args: investment_memory_answer(args.get("question", "")), question_param)
    _register(
        "investment.refresh_public_wallet",
        "Atualiza snapshot da carteira publica.",
        lambda _args: investment_refresh_public_wallet(),
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "investment_refresh_public_wallet",
        "Atualiza snapshot da carteira publica.",
        lambda _args: investment_refresh_public_wallet(),
        read_only=False,
        requires_confirmation=True,
    )
    _register("investment.watchlist", "Lista watchlist de investimentos.", lambda _args: investment_list_watchlist())
    _register(
        "investment.add_watchlist",
        "Adiciona ticker na watchlist.",
        lambda args: investment_add_watchlist(args.get("ticker", "")),
        ticker_param,
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "investment.remove_watchlist",
        "Remove ticker da watchlist.",
        lambda args: investment_remove_watchlist(args.get("ticker", "")),
        ticker_param,
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "investment.set_price_ceiling",
        "Define preco-teto de um ticker.",
        lambda args: investment_set_price_ceiling(args.get("ticker", ""), args.get("price", "")),
        {
            "ticker": {"type": "string", "description": "Ticker do ativo.", "required": True},
            "price": {"type": "string", "description": "Preco-teto.", "required": True},
        },
        read_only=False,
        requires_confirmation=True,
    )
    _register("investment.auto_ceiling_settings", "Mostra configuracao de preco-teto automatico.", lambda _args: investment_get_auto_ceiling_settings())
    _register(
        "investment.set_auto_ceiling_margin",
        "Define margem do preco-teto automatico.",
        lambda args: investment_set_auto_ceiling_margin(args.get("value", "")),
        {"value": {"type": "string", "description": "Margem desejada.", "required": True}},
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "investment.set_thesis",
        "Salva tese curta para um ticker.",
        lambda args: investment_set_thesis(args.get("ticker", ""), args.get("thesis", "")),
        {
            "ticker": {"type": "string", "description": "Ticker do ativo.", "required": True},
            "thesis": {"type": "string", "description": "Tese curta.", "required": True},
        },
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "investment_add_watchlist",
        "Adiciona ticker na watchlist.",
        lambda args: investment_add_watchlist(args.get("ticker", "")),
        ticker_param,
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "investment_remove_watchlist",
        "Remove ticker da watchlist.",
        lambda args: investment_remove_watchlist(args.get("ticker", "")),
        ticker_param,
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "investment_set_price_ceiling",
        "Define preco-teto de um ticker.",
        lambda args: investment_set_price_ceiling(args.get("ticker", ""), args.get("price", "")),
        {
            "ticker": {"type": "string", "description": "Ticker do ativo.", "required": True},
            "price": {"type": "string", "description": "Preco-teto.", "required": True},
        },
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "investment_set_auto_ceiling_margin",
        "Define margem do preco-teto automatico.",
        lambda args: investment_set_auto_ceiling_margin(args.get("value", "")),
        {"value": {"type": "string", "description": "Margem desejada.", "required": True}},
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "investment_set_thesis",
        "Salva tese curta para um ticker.",
        lambda args: investment_set_thesis(args.get("ticker", ""), args.get("thesis", "")),
        {
            "ticker": {"type": "string", "description": "Ticker do ativo.", "required": True},
            "thesis": {"type": "string", "description": "Tese curta.", "required": True},
        },
        read_only=False,
        requires_confirmation=True,
    )
