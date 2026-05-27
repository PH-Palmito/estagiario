from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from llm.gemini_tts_client import synthesize_gemini_tts_to_wav
from voice.audio_effects import apply_jarvis_audio_effect
from voice.audio_files import tts_cache_path, wav_duration_seconds
from voice.audio_playback import play_wav, play_wav_chunk, wait_for_wav_playback
from voice.gemini_tts_utils import gemini_tts_plan
from voice.windows_tts import monitor_windows_tts_process, windows_tts_error, windows_tts_plan


@dataclass(frozen=True)
class TtsRuntimeResult:
    ok: bool
    text: str = ""
    error: str = ""


def wait_for_wav_playback_result(path: str | Path, interrupt_pressed: Callable[[], bool]) -> TtsRuntimeResult | None:
    if wait_for_wav_playback(path, wav_duration_seconds, interrupt_pressed):
        return TtsRuntimeResult(ok=False, error="Fala interrompida.")
    return None


def play_wav_result(
    path: str | Path,
    *,
    preferences: dict,
    interrupt_pressed: Callable[[], bool],
    wait_for_playback: bool | None = None,
) -> TtsRuntimeResult | None:
    should_wait = wait_for_playback
    if should_wait is None:
        should_wait = bool(preferences.get("tts_wait_for_playback", True))

    if play_wav(path, wav_duration_seconds, interrupt_pressed, should_wait):
        return TtsRuntimeResult(ok=False, error="Fala interrompida.")
    return None


def play_wav_chunk_result(path: str | Path, interrupt_pressed: Callable[[], bool]) -> TtsRuntimeResult | None:
    if play_wav_chunk(path, wav_duration_seconds, interrupt_pressed):
        return TtsRuntimeResult(ok=False, error="Fala interrompida.")
    return None


def speak_with_gemini_runtime(
    text: str,
    *,
    preferences: dict,
    prepare_tts_text: Callable[[str], str],
    int_pref: Callable[[str, int, int, int], int],
    interrupt_pressed: Callable[[], bool],
    wait_for_playback: bool | None = None,
) -> TtsRuntimeResult:
    text_for_tts = prepare_tts_text(text)
    timeout_seconds = int_pref("gemini_tts_timeout_seconds", 60, 10, 180)
    plan = gemini_tts_plan(text_for_tts, preferences, timeout_seconds)

    cache_path = None
    if plan.cache_enabled:
        cache_path = tts_cache_path("gemini", plan.text, plan.cache_settings)
        if cache_path.exists():
            interrupted = play_wav_result(
                cache_path,
                preferences=preferences,
                interrupt_pressed=interrupt_pressed,
                wait_for_playback=wait_for_playback,
            )
            if interrupted:
                return interrupted
            return TtsRuntimeResult(ok=True, text=text)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        output_path = temp_file.name

    try:
        synthesize_gemini_tts_to_wav(
            plan.text,
            output_path,
            voice_name=plan.voice_name,
            language_code=plan.language_code,
            timeout_seconds=plan.timeout_seconds,
        )
        apply_jarvis_audio_effect(output_path, preferences)

        play_path = output_path
        if cache_path:
            shutil.copy2(output_path, cache_path)
            play_path = str(cache_path)

        interrupted = play_wav_result(
            play_path,
            preferences=preferences,
            interrupt_pressed=interrupt_pressed,
            wait_for_playback=wait_for_playback,
        )
        if interrupted:
            return interrupted

        return TtsRuntimeResult(ok=True, text=text)
    except Exception as exc:
        return TtsRuntimeResult(ok=False, error=f"Gemini TTS falhou: {exc}")
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass


def speak_with_windows_runtime(
    text: str,
    *,
    culture: str | None,
    preferences: dict,
    powershell_exe: str,
    interrupt_pressed: Callable[[], bool],
    popen: Callable[..., object] = subprocess.Popen,
) -> TtsRuntimeResult:
    plan = windows_tts_plan(text, culture, preferences, powershell_exe)

    try:
        process = popen(
            plan.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        monitor_result = monitor_windows_tts_process(
            process,
            interrupt_pressed,
            time.monotonic,
            time.sleep,
        )
    except Exception as exc:
        return TtsRuntimeResult(ok=False, error=f"Falha ao iniciar voz sintetizada: {exc}")

    if monitor_result.error:
        return TtsRuntimeResult(ok=False, error=monitor_result.error)

    error = windows_tts_error(monitor_result.completed)
    if error:
        return TtsRuntimeResult(ok=False, error=error)

    return TtsRuntimeResult(ok=True, text=text)
