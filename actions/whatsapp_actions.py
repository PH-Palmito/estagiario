from __future__ import annotations

from actions.registry import ActionSpec, register_action
from tools.whatsapp_tools import simulate_whatsapp_message, start_whatsapp_bridge, whatsapp_bridge_status


def _register(name: str, description: str, handler, parameters: dict | None = None, read_only: bool = True) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category="whatsapp",
            read_only=read_only,
            parameters=parameters or {},
        )
    )


def register_whatsapp_actions() -> None:
    _register("whatsapp.status", "Mostra status da ponte local do WhatsApp.", lambda _args: whatsapp_bridge_status())
    _register("whatsapp.start_local_bridge", "Inicia ponte local do WhatsApp.", lambda _args: start_whatsapp_bridge())
    _register(
        "whatsapp.simulate_message",
        "Simula mensagem recebida pelo WhatsApp local.",
        lambda args: simulate_whatsapp_message(args.get("text", ""), args.get("sender") or None),
        {
            "text": {"type": "string", "description": "Mensagem simulada.", "required": True},
            "sender": {"type": "string", "description": "Numero remetente opcional."},
        },
    )
