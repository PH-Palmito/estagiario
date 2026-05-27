from __future__ import annotations

import shutil
import subprocess
import tempfile
from collections.abc import Callable
from pathlib import Path
from typing import Any

from voice.audio_files import tts_cache_path
from voice.piper_utils import piper_cache_settings, piper_cli_command, piper_synthesis_plan
from voice.tts_runtime import TtsRuntimeResult


def piper_cache_key_settings(settings, model: Path, preferences: dict) -> list[str]:
    return piper_cache_settings(
        str(model),
        settings.config_path,
        settings.speaker_id,
        settings.length_scale,
        settings.noise_scale,
        settings.noise_w,
        preferences,
    )


def prime_piper_cache_runtime(
    phrases: list[str],
    *,
    settings,
    model: Path,
    preferences: dict,
    prepare_tts_text: Callable[[str], str],
    apply_audio_effect: Callable[[str], None],
    run_process: Callable[..., Any] = subprocess.run,
) -> TtsRuntimeResult:
    warmed = 0
    skipped = 0
    errors = []

    for phrase in phrases:
        phrase = str(phrase).strip()
        if not phrase:
            continue

        text_for_tts = prepare_tts_text(phrase)
        cache_path = tts_cache_path(
            "piper",
            text_for_tts,
            piper_cache_key_settings(settings, model, preferences),
        )
        if cache_path.exists():
            skipped += 1
            continue

        command = piper_cli_command(settings, str(model), str(cache_path))

        try:
            completed = run_process(
                command,
                input=text_for_tts,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except Exception as exc:
            errors.append(str(exc))
            continue

        if completed.returncode != 0:
            errors.append((completed.stderr or completed.stdout or "Piper falhou.").strip())
            try:
                cache_path.unlink(missing_ok=True)
            except Exception:
                pass
            continue

        apply_audio_effect(str(cache_path))
        warmed += 1

    text = f"Cache TTS: {warmed} criado(s), {skipped} ja existia(m)."
    if errors:
        return TtsRuntimeResult(ok=False, text=text, error=errors[0])

    return TtsRuntimeResult(ok=True, text=text)


def speak_with_piper_runtime(
    text: str,
    *,
    settings,
    model: Path,
    preferences: dict,
    prepare_tts_text: Callable[[str], str],
    run_piper_synthesis: Callable[[str, str, object, Path], TtsRuntimeResult | None],
    play_wav: Callable[[str | Path], TtsRuntimeResult | None],
    play_wav_chunk: Callable[[str | Path], TtsRuntimeResult | None],
    copy_file: Callable[[str | Path, str | Path], object] = shutil.copy2,
) -> TtsRuntimeResult:
    text_for_tts = prepare_tts_text(text)
    cache_settings = piper_cache_key_settings(settings, model, preferences)
    plan = piper_synthesis_plan(text_for_tts, cache_settings, preferences)

    cache_path = None
    if plan.cache_enabled:
        cache_path = tts_cache_path("piper", plan.text, plan.cache_settings)
        if cache_path.exists():
            interrupted = play_wav(cache_path)
            if interrupted:
                return interrupted
            return TtsRuntimeResult(ok=True, text=text)

    if plan.should_chunk:
        for chunk_text in plan.chunks:
            chunk_cache_path = None
            if plan.cache_enabled:
                chunk_cache_path = tts_cache_path("piper", chunk_text, plan.cache_settings)
                if chunk_cache_path.exists():
                    interrupted = play_wav_chunk(chunk_cache_path)
                    if interrupted:
                        return interrupted
                    continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                chunk_output_path = temp_file.name

            try:
                error_result = run_piper_synthesis(chunk_text, chunk_output_path, settings, model)
                if error_result:
                    return error_result

                play_path = chunk_output_path
                if chunk_cache_path:
                    copy_file(chunk_output_path, chunk_cache_path)
                    play_path = str(chunk_cache_path)

                interrupted = play_wav_chunk(play_path)
                if interrupted:
                    return interrupted
            finally:
                try:
                    Path(chunk_output_path).unlink(missing_ok=True)
                except Exception:
                    pass

        return TtsRuntimeResult(ok=True, text=text)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        output_path = temp_file.name

    try:
        error_result = run_piper_synthesis(plan.text, output_path, settings, model)
        if error_result:
            return error_result
        play_path = output_path
        if cache_path:
            copy_file(output_path, cache_path)
            play_path = str(cache_path)

        interrupted = play_wav(play_path)
        if interrupted:
            return interrupted

        return TtsRuntimeResult(ok=True, text=text)
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass
