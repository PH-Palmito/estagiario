from __future__ import annotations

import re
from collections.abc import Callable, MutableMapping

from core.router_utils import normalize_text
from memory.voice_preferences import update_voice_preferences

HUMOR_STYLE_ALIASES = {
    "neutro": "neutro",
    "serio": "neutro",
    "sem humor": "neutro",
    "desligado": "neutro",
    "jarvis": "jarvis",
    "mordomo": "jarvis",
    "sofisticado": "jarvis",
    "elegancia": "jarvis",
    "seco": "seco",
    "ironico": "seco",
    "elegante": "seco",
    "filosofico": "filosofico",
    "reflexivo": "filosofico",
    "visao": "filosofico",
    "brincalhao": "brincalhao",
    "divertido": "brincalhao",
    "leve": "brincalhao",
}

HUMOR_DISPLAY_NAMES = {
    "neutro": "neutro",
    "jarvis": "jarvis",
    "seco": "seco",
    "filosofico": "reflexivo",
    "brincalhao": "leve",
}


def current_humor_description(preferences: MutableMapping[str, object]) -> str:
    enabled = bool(preferences.get("assistant_humor_enabled", True))
    style = str(preferences.get("assistant_humor_style", "seco")).strip().lower()
    try:
        level = int(preferences.get("assistant_humor_level", 2))
    except (TypeError, ValueError):
        level = 2

    if not enabled or style == "neutro" or level <= 0:
        return "Humor atual: neutro, intensidade zero."

    display = HUMOR_DISPLAY_NAMES.get(style, style)
    return f"Humor atual: {display}, intensidade {max(0, min(3, level))} de 3."


def apply_humor_settings(
    preferences: MutableMapping[str, object],
    refresh_preferences: Callable[[], None],
    style: str | None = None,
    level: int | None = None,
    enabled: bool | None = None,
) -> str:
    current_level = int(preferences.get("assistant_humor_level", 2) or 2)
    current_style = str(preferences.get("assistant_humor_style", "seco")).strip().lower() or "seco"

    style = style or current_style
    level = current_level if level is None else max(0, min(3, int(level)))
    enabled = (style != "neutro" and level > 0) if enabled is None else bool(enabled)

    if style == "neutro":
        enabled = False
        level = 0

    update_voice_preferences(
        {
            "assistant_humor_enabled": enabled,
            "assistant_humor_style": style,
            "assistant_humor_level": level,
        }
    )
    preferences.update(
        {
            "assistant_humor_enabled": enabled,
            "assistant_humor_style": style,
            "assistant_humor_level": level,
        }
    )
    refresh_preferences()
    return current_humor_description(preferences)


def humor_test_response(preferences: MutableMapping[str, object]) -> str:
    style = str(preferences.get("assistant_humor_style", "seco")).strip().lower()
    enabled = bool(preferences.get("assistant_humor_enabled", True))
    try:
        level = int(preferences.get("assistant_humor_level", 2))
    except (TypeError, ValueError):
        level = 2

    if not enabled or style == "neutro" or level <= 0:
        return "Teste de humor: sistemas online. Direto, funcional e sem piada lateral. So trabalho."

    if style == "jarvis":
        return "Teste de humor: sistemas online. Tudo sob controle, como deveria ser. Se algo falhar, culparemos a fisica ou o navegador, nessa ordem."

    if style == "filosofico":
        return "Teste de humor: sistemas online. Sempre curioso como um simples comando muda o estado do mundo. E, ainda assim, o mundo insiste em abrir abas demais."

    if style == "brincalhao":
        return "Teste de humor: sistemas online. Tudo em ordem, sem drama e com uma boa vontade quase suspeita. Estou agradavelmente operacional."

    return "Teste de humor: sistemas online. Seco, preciso e com um comentario minimo no ponto certo. A elegancia sobreviveu ao boot."


def maybe_handle_humor_command(
    user_input: str,
    preferences: MutableMapping[str, object],
    refresh_preferences: Callable[[], None],
) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {"testar humor", "teste de humor", "testar personalidade", "teste de personalidade"}:
        return humor_test_response(preferences)

    if normalized in {"humor atual", "qual humor", "qual o humor", "modo humor"}:
        return current_humor_description(preferences)

    if normalized in {"mais humor", "aumentar humor", "aumenta humor"}:
        level = int(preferences.get("assistant_humor_level", 2) or 2)
        return apply_humor_settings(preferences, refresh_preferences, level=level + 1, enabled=True)

    if normalized in {"menos humor", "diminuir humor", "diminui humor"}:
        level = int(preferences.get("assistant_humor_level", 2) or 2)
        return apply_humor_settings(preferences, refresh_preferences, level=level - 1)

    if not any(word in normalized for word in {"humor", "personalidade"}):
        return None

    if any(phrase in normalized for phrase in {"desligar", "desliga", "sem humor", "neutro", "serio"}):
        return apply_humor_settings(preferences, refresh_preferences, style="neutro")

    if any(phrase in normalized for phrase in {"ligar", "liga", "ativar", "ativa"}):
        return apply_humor_settings(
            preferences,
            refresh_preferences,
            style=str(preferences.get("assistant_humor_style", "seco") or "seco"),
            level=max(1, int(preferences.get("assistant_humor_level", 2) or 2)),
            enabled=True,
        )

    for alias, style in HUMOR_STYLE_ALIASES.items():
        if alias in normalized:
            return apply_humor_settings(preferences, refresh_preferences, style=style, level=2 if style != "neutro" else 0)

    level_match = re.search(r"\b(?:nivel|intensidade)\s+([0-3])\b", normalized)
    if level_match:
        level = int(level_match.group(1))
        return apply_humor_settings(preferences, refresh_preferences, level=level)

    return "Nao identifiquei o humor. Tente: humor jarvis, humor seco, humor reflexivo, humor leve ou humor neutro."
