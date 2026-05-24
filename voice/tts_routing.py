from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

INTERRUPTED_TTS_ERROR = "Fala interrompida."


class TtsResult(Protocol):
    ok: bool
    error: str | None


ResultT = TypeVar("ResultT", bound=TtsResult)


def selected_tts_engine(preferences: dict) -> str:
    return str(preferences.get("tts_engine", "windows")).strip().lower()


def tts_can_fallback_to_piper(preferences: dict) -> bool:
    return bool(preferences.get("gemini_tts_fallback_to_piper", True))


def tts_can_fallback_to_windows(preferences: dict) -> bool:
    return bool(preferences.get("piper_fallback_to_windows", True))


def tts_has_piper_model(preferences: dict) -> bool:
    return bool(str(preferences.get("piper_model_path", "")).strip())


def speak_with_tts_routing(
    text: str,
    culture: str | None,
    preferences: dict,
    speak_with_gemini: Callable[[str], ResultT],
    speak_with_piper: Callable[[str], ResultT],
    speak_with_windows: Callable[[str, str | None], ResultT],
) -> ResultT:
    engine = selected_tts_engine(preferences)

    if engine == "gemini":
        result = speak_with_gemini(text)
        if result.ok or result.error == INTERRUPTED_TTS_ERROR or not tts_can_fallback_to_piper(preferences):
            return result

        if tts_has_piper_model(preferences):
            piper_result = speak_with_piper(text)
            if piper_result.ok or piper_result.error == INTERRUPTED_TTS_ERROR:
                return piper_result

        return speak_with_windows(text, culture)

    if engine == "piper":
        result = speak_with_piper(text)
        if result.ok or result.error == INTERRUPTED_TTS_ERROR or not tts_can_fallback_to_windows(preferences):
            return result

    return speak_with_windows(text, culture)
