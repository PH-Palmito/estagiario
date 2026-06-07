from __future__ import annotations

from actions.registry import ActionSpec, register_action
from tools.keyboard_led_tools import keyboard_led_off, keyboard_led_on, keyboard_led_set, keyboard_led_status


def register_keyboard_led_actions() -> None:
    register_action(
        ActionSpec(
            name="keyboard_led_status",
            description="Mostra estado planejado dos LEDs do teclado.",
            handler=lambda _args: keyboard_led_status(),
            category="system",
            read_only=True,
        )
    )
    register_action(
        ActionSpec(
            name="keyboard_led_on",
            description="Liga LEDs do teclado no perfil local configurado.",
            handler=lambda args: keyboard_led_on(args.get("color", ""), args.get("profile", ""), args.get("effect", "")),
            category="system",
            read_only=False,
            requires_confirmation=True,
            parameters={
                "color": {"type": "string", "description": "Cor desejada."},
                "profile": {"type": "string", "description": "Perfil desejado."},
                "effect": {"type": "string", "description": "Efeito desejado."},
            },
        )
    )
    register_action(
        ActionSpec(
            name="keyboard_led_off",
            description="Desliga LEDs do teclado.",
            handler=lambda _args: keyboard_led_off(),
            category="system",
            read_only=False,
            requires_confirmation=True,
        )
    )
    register_action(
        ActionSpec(
            name="keyboard_led_set",
            description="Ajusta cor, perfil ou efeito dos LEDs do teclado.",
            handler=lambda args: keyboard_led_set(
                color=args.get("color", ""),
                profile=args.get("profile", ""),
                effect=args.get("effect", ""),
            ),
            category="system",
            read_only=False,
            requires_confirmation=True,
            parameters={
                "color": {"type": "string", "description": "Cor desejada."},
                "profile": {"type": "string", "description": "Perfil desejado."},
                "effect": {"type": "string", "description": "Efeito desejado."},
            },
        )
    )
