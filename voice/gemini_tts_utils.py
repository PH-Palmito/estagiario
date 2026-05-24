from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GeminiTtsPlan:
    text: str
    voice_name: str
    language_code: str
    timeout_seconds: int
    cache_enabled: bool
    cache_settings: list[str]


def gemini_voice_name(preferences: dict) -> str:
    return str(preferences.get("gemini_tts_voice_name", "Kore")).strip() or "Kore"


def gemini_language_code(preferences: dict) -> str:
    return str(preferences.get("gemini_tts_language_code", "pt-BR")).strip() or "pt-BR"


def gemini_cache_settings(
    voice_name: str,
    language_code: str,
    timeout_seconds: str,
    preferences: dict,
) -> list[str]:
    effect = str(preferences.get("assistant_voice_effect", "")).strip().lower()
    effect_strength = str(preferences.get("assistant_voice_effect_strength", 0.0))
    return [voice_name, language_code, timeout_seconds, effect, effect_strength]


def gemini_tts_plan(
    text_for_tts: str,
    preferences: dict,
    timeout_seconds: int,
) -> GeminiTtsPlan:
    voice_name = gemini_voice_name(preferences)
    language_code = gemini_language_code(preferences)
    return GeminiTtsPlan(
        text=text_for_tts,
        voice_name=voice_name,
        language_code=language_code,
        timeout_seconds=timeout_seconds,
        cache_enabled=bool(preferences.get("tts_cache_enabled", True)),
        cache_settings=gemini_cache_settings(voice_name, language_code, str(timeout_seconds), preferences),
    )
