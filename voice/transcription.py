from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptionResolution:
    ok: bool
    text: str
    error: str | None = None


@dataclass(frozen=True)
class HotwordDetectionResolution:
    ok: bool
    text: str = ""
    command_text: str = ""
    error: str | None = None


@dataclass(frozen=True)
class AudioListenPlan:
    timeout_seconds: float
    min_speech_seconds: float | None = None
    max_silence_seconds: float | None = None


@dataclass(frozen=True)
class TranscriptionPlan:
    model_size: str
    prompt: str | None
    beam_size: int
    best_of: int
    vad_filter: bool


def command_transcription_plan(
    *,
    command_model_size: str,
    command_prompt: str,
    whisper_command_beam_size: int,
    whisper_command_best_of: int,
    whisper_command_vad_filter: bool,
) -> TranscriptionPlan:
    return TranscriptionPlan(
        model_size=command_model_size,
        prompt=command_prompt,
        beam_size=whisper_command_beam_size,
        best_of=whisper_command_best_of,
        vad_filter=whisper_command_vad_filter,
    )


def hotword_listen_plan(
    *,
    timeout_seconds: float,
    min_speech_seconds: float,
    max_silence_seconds: float,
) -> AudioListenPlan:
    return AudioListenPlan(
        timeout_seconds=timeout_seconds,
        min_speech_seconds=min_speech_seconds,
        max_silence_seconds=max_silence_seconds,
    )


def hotword_transcription_plan(
    *,
    hotword_model_size: str,
    hotword_prompt: str,
    whisper_hotword_beam_size: int,
    whisper_hotword_best_of: int,
    whisper_hotword_vad_filter: bool,
) -> TranscriptionPlan:
    return TranscriptionPlan(
        model_size=hotword_model_size,
        prompt=hotword_prompt,
        beam_size=whisper_hotword_beam_size,
        best_of=whisper_hotword_best_of,
        vad_filter=whisper_hotword_vad_filter,
    )


def conversation_listen_plan(
    *,
    requested_timeout_seconds: float | None,
    default_timeout_seconds: float,
    min_speech_seconds: float,
    max_silence_seconds: float,
) -> AudioListenPlan:
    return AudioListenPlan(
        timeout_seconds=requested_timeout_seconds or default_timeout_seconds,
        min_speech_seconds=min_speech_seconds,
        max_silence_seconds=max_silence_seconds,
    )


def conversation_transcription_plan(
    *,
    conversation_model_size: str,
    conversation_prompt: str,
    whisper_conversation_beam_size: int,
    whisper_conversation_best_of: int,
    whisper_conversation_vad_filter: bool,
) -> TranscriptionPlan:
    return TranscriptionPlan(
        model_size=conversation_model_size,
        prompt=conversation_prompt,
        beam_size=whisper_conversation_beam_size,
        best_of=whisper_conversation_best_of,
        vad_filter=whisper_conversation_vad_filter,
    )


def resolve_hotword_detection(
    *,
    hotword_text: str,
    hotword: str,
    contains_hotword: Callable[[str, str], bool],
    transcribe_command: Callable[[], TranscriptionResolution],
    extract_inline_command: Callable[[str, str], str],
) -> HotwordDetectionResolution:
    if not contains_hotword(hotword_text, hotword):
        return HotwordDetectionResolution(ok=False, error="Hotword nao detectada.")

    command_result = transcribe_command()
    if command_result.ok:
        return HotwordDetectionResolution(
            ok=True,
            text=hotword_text,
            command_text=extract_inline_command(command_result.text, hotword),
        )

    return HotwordDetectionResolution(ok=True, text=hotword_text)


def resolve_transcription_text(
    text: str,
    *,
    model_size: str,
    command_model_size: str,
    prompt: str | None,
    command_prompt: str,
    command_rescue_prompt: str,
    beam_size: int,
    best_of: int,
    prompt_hallucination_error: str,
    transcribe_once: Callable[[str | None, int, int, bool], tuple[str, object]],
    is_prompt_hallucination: Callable[[str], bool],
    should_retry_command_transcription: Callable[[str], bool],
    command_transcription_score: Callable[[str], float],
) -> TranscriptionResolution:
    if not text:
        return TranscriptionResolution(ok=False, text="", error="Nenhuma fala reconhecida.")

    resolved_text = text
    if model_size == command_model_size and is_prompt_hallucination(resolved_text):
        rescue_text, _rescue_info = transcribe_once(
            None,
            max(beam_size, 6),
            max(best_of, 6),
            False,
        )
        if rescue_text and not is_prompt_hallucination(rescue_text):
            resolved_text = rescue_text
        else:
            return TranscriptionResolution(ok=False, text="", error=prompt_hallucination_error)

    if (
        model_size == command_model_size
        and prompt == command_prompt
        and should_retry_command_transcription(resolved_text)
    ):
        rescue_text, _rescue_info = transcribe_once(
            command_rescue_prompt,
            max(beam_size, 6),
            max(best_of, 6),
            False,
        )
        if rescue_text and command_transcription_score(rescue_text) > command_transcription_score(resolved_text):
            resolved_text = rescue_text

    return TranscriptionResolution(ok=True, text=resolved_text)
