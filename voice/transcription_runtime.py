from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from voice.transcription import TranscriptionResolution


@dataclass(frozen=True)
class WhisperTranscriptionConfig:
    command_model_size: str
    command_prompt: str
    command_rescue_prompt: str


def transcribe_audio(
    *,
    audio: np.ndarray,
    model_size: str,
    prompt: str | None,
    beam_size: int,
    best_of: int,
    vad_filter: bool,
    preprocess: bool,
    config: WhisperTranscriptionConfig,
    audio_has_signal: Callable[[np.ndarray], bool],
    preprocess_audio: Callable[[np.ndarray], np.ndarray],
    save_temp_wav: Callable[[np.ndarray], str],
    get_model: Callable[[str], object],
    resolve_transcription_text: Callable[..., TranscriptionResolution],
    is_prompt_hallucination: Callable[[str], bool],
    should_retry_command_transcription: Callable[[str], bool],
    command_transcription_score: Callable[[str], float],
) -> TranscriptionResolution:
    if not audio_has_signal(audio):
        return TranscriptionResolution(ok=False, text="", error="Nao detectei fala no microfone.")

    def transcribe_once(active_prompt: str | None, active_beam: int, active_best_of: int, active_vad: bool):
        processed_audio = preprocess_audio(audio) if preprocess else audio
        active_temp_path = save_temp_wav(processed_audio)
        try:
            model = get_model(model_size)
            segments, info = model.transcribe(
                active_temp_path,
                language="pt",
                task="transcribe",
                vad_filter=active_vad,
                beam_size=active_beam,
                best_of=active_best_of,
                temperature=0.0,
                initial_prompt=active_prompt or None,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text.strip() for segment in segments).strip()
            return text, info
        finally:
            if active_temp_path and os.path.exists(active_temp_path):
                os.remove(active_temp_path)

    try:
        text, info = transcribe_once(prompt, beam_size, best_of, vad_filter)

        resolution = resolve_transcription_text(
            text,
            model_size=model_size,
            command_model_size=config.command_model_size,
            prompt=prompt,
            command_prompt=config.command_prompt,
            command_rescue_prompt=config.command_rescue_prompt,
            beam_size=beam_size,
            best_of=best_of,
            prompt_hallucination_error="Nao captei com precisao.",
            transcribe_once=transcribe_once,
            is_prompt_hallucination=is_prompt_hallucination,
            should_retry_command_transcription=should_retry_command_transcription,
            command_transcription_score=command_transcription_score,
        )
        if not resolution.ok:
            return resolution

        language_probability = getattr(info, "language_probability", None)
        if language_probability is not None and language_probability < 0.25:
            return TranscriptionResolution(ok=True, text=resolution.text)

        return TranscriptionResolution(ok=True, text=resolution.text)
    except Exception as exc:
        return TranscriptionResolution(ok=False, text="", error=f"Falha ao transcrever audio: {exc}")
