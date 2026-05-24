from __future__ import annotations

from collections.abc import Callable, MutableMapping

from core.router_utils import normalize_text
from memory.voice_profiles import apply_voice_profile, list_voice_profiles


def voice_profile_from_text(text: str) -> str | None:
    normalized = normalize_text(text)
    profile_aliases = {
        "faber rapido": "faber-rapido",
        "voz rapida": "faber-rapido",
        "faber claro": "faber-claro",
        "voz clara": "faber-claro",
        "faber calmo": "faber-calmo",
        "faber calma": "faber-calmo",
        "voz calma": "faber-calmo",
        "faber jarvis": "faber-jarvis",
        "faber jervis": "faber-jarvis",
        "voz jarvis faber": "faber-jarvis",
        "jarvis faber": "faber-jarvis",
        "modo jarvis faber": "faber-jarvis",
        "assistente": "assistente",
        "assistente natural": "assistente",
        "assistente cinema": "assistente-cinema",
        "assistente cinematografico": "assistente-cinema",
        "modo jarvis": "assistente-cinema",
        "modo cinema": "assistente-cinema",
        "estagiario": "assistente",
        "estagiario natural": "assistente",
        "jarvis": "jarvis",
        "jarves": "jarvis",
        "jarvis limpo": "jarvis",
        "jarvis calmo": "jarvis-calmo",
        "jarvis calma": "jarvis-calmo",
        "jarvis firme": "jarvis-firme",
        "jarvis forte": "jarvis-firme",
        "jarvis console": "jarvis-console",
        "jarvis com efeito": "jarvis-console",
        "console": "jarvis-console",
        "natural": "natural",
        "normal": "natural",
        "padrao": "natural",
    }

    for alias, profile in sorted(profile_aliases.items(), key=lambda item: len(item[0]), reverse=True):
        if alias in normalized:
            return profile

    return None


def maybe_handle_voice_profile_command(
    user_input: str,
    preferences: MutableMapping[str, object],
    refresh_preferences: Callable[[], None],
) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "listar vozes",
        "listar perfis de voz",
        "quais vozes",
        "quais vozes voce tem",
        "opcoes de voz",
        "opcoes da voz",
    }:
        return "Perfis de voz: " + ", ".join(list_voice_profiles()) + "."

    if normalized in {"testar voz", "teste de voz", "teste da voz", "fala teste"}:
        return str(preferences.get("startup_voice_greeting", "")).strip() or "Sistemas online. A sua disposicao."

    change_voice_prefixes = (
        "mudar voz",
        "trocar voz",
        "usar voz",
        "ativar voz",
        "voz ",
        "perfil de voz",
        "deixa a voz",
        "deixar a voz",
    )
    explicit_voice_phrases = {
        "voz rapida",
        "voz clara",
        "voz calma",
        "voz jarvis faber",
        "voz assistente",
        "voz cinema",
        "voz estagiario",
        "voz jarvis",
        "voz natural",
        "voz normal",
        "voz padrao",
        "voz console",
    }
    if not normalized.startswith(change_voice_prefixes) and not any(
        phrase in normalized for phrase in explicit_voice_phrases
    ):
        return None

    profile = voice_profile_from_text(normalized)
    if not profile:
        return "Nao identifiquei o perfil de voz. Diga, por exemplo, voz jarvis firme ou voz natural."

    ok, message = apply_voice_profile(profile)
    refresh_preferences()
    if ok:
        return f"{message} {preferences.get('startup_voice_greeting', 'Sistemas online.')}"

    return message
