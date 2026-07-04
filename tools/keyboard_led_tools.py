from __future__ import annotations

import json
from pathlib import Path


KEYBOARD_LED_STATE_PATH = Path("memory/keyboard_led_state.json")

DEFAULT_KEYBOARD_LED_STATE = {
    "enabled": False,
    "color": "branco",
    "profile": "padrao",
    "effect": "static",
    "provider": "simulated",
}


def _load_state() -> dict:
    try:
        if KEYBOARD_LED_STATE_PATH.exists():
            data = json.loads(KEYBOARD_LED_STATE_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return {**DEFAULT_KEYBOARD_LED_STATE, **data}
    except Exception:
        pass
    return dict(DEFAULT_KEYBOARD_LED_STATE)


def _save_state(state: dict) -> dict:
    KEYBOARD_LED_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {**DEFAULT_KEYBOARD_LED_STATE, **state}
    KEYBOARD_LED_STATE_PATH.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def keyboard_led_status() -> str:
    state = _load_state()
    mode = "ligado" if state.get("enabled") else "desligado"
    return (
        "LED do teclado: "
        f"{mode}; cor {state.get('color')}; perfil {state.get('profile')}; "
        f"efeito {state.get('effect')}. "
        "Primeira camada plugável: driver físico ainda não configurado; estado salvo em modo simulado."
    )


def keyboard_led_set(
    *,
    enabled: bool | None = None,
    color: str = "",
    profile: str = "",
    effect: str = "",
) -> str:
    state = _load_state()
    if enabled is not None:
        state["enabled"] = bool(enabled)
    if color:
        state["color"] = str(color).strip().lower()
    if profile:
        state["profile"] = str(profile).strip().lower()
    if effect:
        state["effect"] = str(effect).strip().lower()
    saved = _save_state(state)
    mode = "ligado" if saved.get("enabled") else "desligado"
    return (
        f"LED do teclado {mode}: cor {saved.get('color')}, perfil {saved.get('profile')}, "
        f"efeito {saved.get('effect')}. "
        "Primeira camada plugável: modo simulado ativo até conectar um provedor físico compatível."
    )


def keyboard_led_on(color: str = "", profile: str = "", effect: str = "") -> str:
    return keyboard_led_set(enabled=True, color=color, profile=profile, effect=effect)


def keyboard_led_off() -> str:
    return keyboard_led_set(enabled=False)
