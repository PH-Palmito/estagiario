from __future__ import annotations

from actions.registry import ActionSpec, register_action
from tools.telegram_tools import (
    simulate_telegram_message,
    start_telegram_bridge,
    telegram_bridge_status,
    telegram_recent_chats,
)


def _register(name: str, description: str, handler, *, read_only: bool = True) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category="telegram",
            read_only=read_only,
        )
    )


def register_telegram_actions() -> None:
    _register("telegram.status", "Mostra status do Telegram Bot do Axel.", lambda _args: telegram_bridge_status())
    _register("telegram.recent_chats", "Lista chats recentes para descobrir o chat_id autorizado.", lambda _args: telegram_recent_chats())
    _register("telegram.start_bot", "Inicia polling local do Telegram Bot.", lambda _args: start_telegram_bridge())
    _register(
        "telegram.simulate_message",
        "Simula uma mensagem recebida pelo Telegram Bot.",
        lambda args: simulate_telegram_message(args.get("text", ""), args.get("chat_id") or None),
    )
