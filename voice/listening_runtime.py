from __future__ import annotations

from collections.abc import Callable

import numpy as np

from voice.transcription import AudioListenPlan, HotwordDetectionResolution, TranscriptionPlan, TranscriptionResolution


def listen_for_hotword(
    *,
    hotword: str,
    listen_plan: AudioListenPlan,
    hotword_plan: TranscriptionPlan,
    command_plan: TranscriptionPlan,
    record_audio: Callable[..., np.ndarray],
    transcribe_audio: Callable[..., object],
    resolve_hotword_detection: Callable[..., HotwordDetectionResolution],
    contains_hotword: Callable[[str, str], bool],
    extract_inline_command: Callable[[str, str], str],
) -> HotwordDetectionResolution:
    try:
        audio = record_audio(
            listen_plan.timeout_seconds,
            min_speech_seconds=listen_plan.min_speech_seconds,
            max_silence_seconds=listen_plan.max_silence_seconds,
        )
    except Exception as exc:
        return HotwordDetectionResolution(ok=False, error=f"Falha ao acessar o microfone: {exc}")

    result = transcribe_audio(
        audio=audio,
        model_size=hotword_plan.model_size,
        prompt=hotword_plan.prompt,
        beam_size=hotword_plan.beam_size,
        best_of=hotword_plan.best_of,
        vad_filter=hotword_plan.vad_filter,
    )

    if not result.ok:
        return HotwordDetectionResolution(ok=False, error=result.error)

    def transcribe_inline_command():
        command_result = transcribe_audio(
            audio=audio,
            model_size=command_plan.model_size,
            prompt=command_plan.prompt,
            beam_size=command_plan.beam_size,
            best_of=command_plan.best_of,
            vad_filter=command_plan.vad_filter,
        )
        return TranscriptionResolution(
            ok=command_result.ok,
            text=command_result.text,
            error=command_result.error,
        )

    return resolve_hotword_detection(
        hotword_text=result.text,
        hotword=hotword,
        contains_hotword=contains_hotword,
        transcribe_command=transcribe_inline_command,
        extract_inline_command=extract_inline_command,
    )


def listen_once(
    *,
    timeout_seconds: float,
    transcription_plan: TranscriptionPlan,
    record_audio: Callable[..., np.ndarray],
    transcribe_audio: Callable[..., object],
) -> TranscriptionResolution:
    try:
        audio = record_audio(timeout_seconds)
    except Exception as exc:
        return TranscriptionResolution(ok=False, text="", error=f"Falha ao acessar o microfone: {exc}")

    result = transcribe_audio(
        audio=audio,
        model_size=transcription_plan.model_size,
        prompt=transcription_plan.prompt,
        beam_size=transcription_plan.beam_size,
        best_of=transcription_plan.best_of,
        vad_filter=transcription_plan.vad_filter,
    )
    return TranscriptionResolution(ok=result.ok, text=result.text, error=result.error)


def listen_conversation_once(
    *,
    listen_plan: AudioListenPlan,
    transcription_plan: TranscriptionPlan,
    record_audio: Callable[..., np.ndarray],
    transcribe_audio: Callable[..., object],
) -> TranscriptionResolution:
    try:
        audio = record_audio(
            listen_plan.timeout_seconds,
            min_speech_seconds=listen_plan.min_speech_seconds,
            max_silence_seconds=listen_plan.max_silence_seconds,
        )
    except Exception as exc:
        return TranscriptionResolution(ok=False, text="", error=f"Falha ao acessar o microfone: {exc}")

    result = transcribe_audio(
        audio=audio,
        model_size=transcription_plan.model_size,
        prompt=transcription_plan.prompt,
        beam_size=transcription_plan.beam_size,
        best_of=transcription_plan.best_of,
        vad_filter=transcription_plan.vad_filter,
    )
    return TranscriptionResolution(ok=result.ok, text=result.text, error=result.error)
