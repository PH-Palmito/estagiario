from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime
from threading import Thread


def startup_greeting_message(
    *,
    argv: Sequence[str],
    voice_preferences: dict,
    greeting_variants: dict[str, tuple[str, ...]],
    contextual_startup_phrase: Callable[..., str],
    next_phrase: Callable[..., str],
    now: datetime | None = None,
) -> str:
    configured = str(voice_preferences.get("startup_voice_greeting", "")).strip()
    if configured and not bool(voice_preferences.get("startup_voice_greeting_variants_enabled", True)):
        return configured

    compact_interactive_startup = any(flag in argv for flag in ("--voice", "--hotword", "--ui"))
    if "--startup" in argv:
        category = "computer_startup"
    elif "--short-startup-greeting" in argv or compact_interactive_startup:
        category = "short_ready"
    else:
        category = str(voice_preferences.get("startup_voice_greeting_category", "study_code")).strip()

    if category not in greeting_variants:
        category = "study_code"

    autonomous = bool(voice_preferences.get("startup_voice_autonomous_variation_enabled", True))
    address_user = str(voice_preferences.get("assistant_address_user", "chefe")).strip() or "chefe"
    if autonomous:
        hour = (now or datetime.now()).hour
        if hour < 12:
            greeting = "Bom dia"
        elif hour < 18:
            greeting = "Boa tarde"
        else:
            greeting = "Boa noite"

        composed = contextual_startup_phrase(
            category,
            address_user=address_user,
            greeting=greeting,
        )
        if composed:
            return composed

    return next_phrase(
        f"startup_greeting_{category}",
        greeting_variants[category],
        configured or "Sistemas online. Pronto para começar.",
    )


def common_tts_cache_phrases(
    *,
    voice_preferences: dict,
    style_response: Callable[[str], str],
) -> list[str]:
    phrases = [
        str(
            voice_preferences.get(
                "startup_voice_greeting",
                "Modo voz ativado. Pronto para começar.",
            )
        ).strip(),
        "Pode falar.",
        "Pode falar...",
        "Pode responder...",
        "Nao entendi.",
        "Pode repetir?",
        "Nao identifiquei o comando.",
        "Abrindo Spotify.",
        "Fechando Spotify.",
        "Abrindo Chrome.",
        "Abrindo VS Code.",
        "Fechando VS Code.",
        "Escuta pausada.",
        "Escuta retomada.",
        "Acao cancelada.",
        "Encerrando.",
    ]
    styled = [style_response(phrase) for phrase in phrases if phrase]
    return list(dict.fromkeys(styled))


def warm_common_tts_cache_async(
    *,
    voice_preferences: dict,
    common_tts_cache_phrases: Callable[[], list[str]],
    prime_piper_cache: Callable[[list[str]], object],
    thread_factory: Callable[..., object] = Thread,
) -> bool:
    if str(voice_preferences.get("tts_engine", "")).strip().lower() != "piper":
        return False

    if not bool(voice_preferences.get("tts_cache_enabled", True)):
        return False

    if not bool(voice_preferences.get("tts_warm_cache_on_startup", True)):
        return False

    try:
        thread = thread_factory(
            target=lambda: prime_piper_cache(common_tts_cache_phrases()),
            daemon=True,
        )
        thread.start()
        return True
    except Exception:
        return False
