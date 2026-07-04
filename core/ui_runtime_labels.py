from __future__ import annotations

from collections.abc import Mapping


def assistant_style_label(preferences: Mapping[str, object]) -> str:
    assistant_style = str(preferences.get("assistant_style", "")).strip().lower()
    if assistant_style in {"axel", "jarvis", "assistente", "elegante"}:
        return assistant_style

    humor_enabled = bool(preferences.get("assistant_humor_enabled", True))
    humor_style = str(preferences.get("assistant_humor_style", "")).strip().lower()
    if humor_enabled and humor_style:
        return humor_style

    return "padrao"


def voice_profile_label(preferences: Mapping[str, object]) -> str:
    for key in (
        "voice_profile_name",
        "voice_profile",
        "piper_voice",
        "tts_voice",
        "tts_speaker",
    ):
        value = str(preferences.get(key, "")).strip()
        if value:
            return value
    return "faber"


def ui_mode_label(
    *,
    dictation_mode: bool,
    conversation_mode: bool,
    waiting_for_direct_response: bool,
) -> str:
    if dictation_mode:
        return "ditado"
    if conversation_mode:
        return "conversa"
    if waiting_for_direct_response:
        return "resposta"
    return "comando"
