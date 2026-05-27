import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from memory.voice_preferences import load_voice_preferences
from voice.audio_capture import (
    audio_has_signal as _audio_has_signal_core,
)
from voice.audio_capture import (
    chunk_has_speech as _chunk_has_speech_core,
)
from voice.audio_capture import (
    chunk_levels as _chunk_levels_core,
)
from voice.audio_capture import (
    preprocess_audio as _preprocess_audio_core,
)
from voice.audio_capture import (
    record_audio as _record_audio_core,
)
from voice.audio_capture import (
    record_fixed_audio as _record_fixed_audio_core,
)
from voice.audio_diagnostics import format_audio_stats as _format_audio_stats_core
from voice.audio_diagnostics import run_audio_diagnostic as _run_audio_diagnostic_core
from voice.audio_effects import (
    apply_jarvis_audio_effect as _apply_jarvis_audio_effect_core,
)
from voice.audio_files import (
    save_temp_wav as _save_temp_wav_core,
)
from voice.audio_files import (
    save_wav as _save_wav_core,
)
from voice.audio_playback import (
    stop_playback as _stop_playback_core,
)
from voice.hotkeys import (
    consume_key_press as _consume_key_press_core,
)
from voice.hotkeys import (
    play_activation_sound as _play_activation_sound_core,
)
from voice.input_devices import (
    format_input_devices as _format_input_devices_core,
)
from voice.input_devices import (
    list_input_devices as _list_input_devices_core,
)
from voice.input_devices import (
    resolve_input_device as _resolve_input_device_core,
)
from voice.listening_runtime import listen_conversation_once as _listen_conversation_once_core
from voice.listening_runtime import listen_for_hotword as _listen_for_hotword_core
from voice.listening_runtime import listen_once as _listen_once_core
from voice.piper_runtime import run_piper_synthesis as _run_piper_synthesis_core
from voice.piper_speech import prime_piper_cache_runtime as _prime_piper_cache_runtime_core
from voice.piper_speech import speak_with_piper_runtime as _speak_with_piper_runtime_core
from voice.piper_utils import (
    piper_tts_settings as _piper_tts_settings_core,
)
from voice.piper_utils import (
    validate_piper_tts_settings as _validate_piper_tts_settings_core,
)
from voice.recognition_text import (
    command_transcription_score as _command_transcription_score,
)
from voice.recognition_text import (
    contains_hotword as _recognition_contains_hotword,
)
from voice.recognition_text import (
    extract_inline_command as _recognition_extract_inline_command,
)
from voice.recognition_text import (
    is_prompt_hallucination as _recognition_is_prompt_hallucination,
)
from voice.recognition_text import (
    should_retry_command_transcription as _should_retry_command_transcription,
)
from voice.transcription import command_transcription_plan as _command_transcription_plan_core
from voice.transcription import conversation_listen_plan as _conversation_listen_plan_core
from voice.transcription import conversation_transcription_plan as _conversation_transcription_plan_core
from voice.transcription import hotword_listen_plan as _hotword_listen_plan_core
from voice.transcription import hotword_transcription_plan as _hotword_transcription_plan_core
from voice.transcription import resolve_hotword_detection as _resolve_hotword_detection_core
from voice.transcription import resolve_transcription_text as _resolve_transcription_text_core
from voice.transcription_runtime import WhisperTranscriptionConfig
from voice.transcription_runtime import transcribe_audio as _transcribe_audio_core
from voice.tts_routing import speak_with_tts_routing as _speak_with_tts_routing_core
from voice.tts_runtime import (
    play_wav_chunk_result as _play_wav_chunk_result_core,
)
from voice.tts_runtime import (
    play_wav_result as _play_wav_result_core,
)
from voice.tts_runtime import (
    speak_with_gemini_runtime as _speak_with_gemini_runtime_core,
)
from voice.tts_runtime import (
    speak_with_windows_runtime as _speak_with_windows_runtime_core,
)
from voice.tts_runtime import (
    wait_for_wav_playback_result as _wait_for_wav_playback_result_core,
)
from voice.tts_text import (
    load_tts_pronunciations as _load_tts_pronunciations_core,
)
from voice.tts_text import (
    prepare_tts_text as _prepare_tts_text_core,
)
from voice.whisper_models import (
    get_model as _get_model_core,
)
from voice.windows_tts import clamp_int as _clamp_int_core
from voice.windows_voice_config import (
    COMMAND_MODEL_SIZE,
    COMMAND_PROMPT,
    COMMAND_RESCUE_PROMPT,
    HOTWORD_MODEL_SIZE,
    SAMPLE_RATE,
    TTS_PRONUNCIATIONS_PATH,
    build_voice_runtime_config,
)
from voice.windows_voice_config import (
    float_pref as _float_pref_core,
)
from voice.windows_voice_config import (
    int_pref as _int_pref_core,
)

POWERSHELL_EXE = "powershell"
VOICE_PREFERENCES = load_voice_preferences()
VOICE_CONFIG = build_voice_runtime_config(VOICE_PREFERENCES)
_TTS_WAIT_FOR_PLAYBACK_OVERRIDE = None


def _float_pref(name: str, default: float, minimum: float, maximum: float) -> float:
    return _float_pref_core(VOICE_PREFERENCES, name, default, minimum, maximum)


def _int_pref(name: str, default: int, minimum: int, maximum: int) -> int:
    return _int_pref_core(VOICE_PREFERENCES, name, default, minimum, maximum)


CONVERSATION_MODEL_SIZE = VOICE_CONFIG.conversation_model_size
DEFAULT_MIN_SPEECH_SECONDS = VOICE_CONFIG.default_min_speech_seconds
DEFAULT_MAX_SILENCE_SECONDS = VOICE_CONFIG.default_max_silence_seconds
AUDIO_DIAGNOSTIC_SECONDS = VOICE_CONFIG.audio_diagnostic_seconds
WHISPER_COMMAND_VAD_FILTER = VOICE_CONFIG.whisper_command_vad_filter
WHISPER_CONVERSATION_VAD_FILTER = VOICE_CONFIG.whisper_conversation_vad_filter
WHISPER_HOTWORD_VAD_FILTER = VOICE_CONFIG.whisper_hotword_vad_filter
WHISPER_COMMAND_BEAM_SIZE = VOICE_CONFIG.whisper_command_beam_size
WHISPER_COMMAND_BEST_OF = VOICE_CONFIG.whisper_command_best_of
WHISPER_CONVERSATION_BEAM_SIZE = VOICE_CONFIG.whisper_conversation_beam_size
WHISPER_CONVERSATION_BEST_OF = VOICE_CONFIG.whisper_conversation_best_of
WHISPER_HOTWORD_BEAM_SIZE = VOICE_CONFIG.whisper_hotword_beam_size
WHISPER_HOTWORD_BEST_OF = VOICE_CONFIG.whisper_hotword_best_of
HOTWORD = VOICE_CONFIG.hotword
HOTWORD_LISTENING_ENABLED = VOICE_CONFIG.hotword_listening_enabled
HOTWORD_TIMEOUT_SECONDS = VOICE_CONFIG.hotword_timeout_seconds
HOTWORD_MAX_SILENCE_SECONDS = VOICE_CONFIG.hotword_max_silence_seconds
HOTWORD_MIN_SPEECH_SECONDS = VOICE_CONFIG.hotword_min_speech_seconds
CONVERSATION_TIMEOUT_SECONDS = VOICE_CONFIG.conversation_timeout_seconds
CONVERSATION_MAX_SILENCE_SECONDS = VOICE_CONFIG.conversation_max_silence_seconds
CONVERSATION_MIN_SPEECH_SECONDS = VOICE_CONFIG.conversation_min_speech_seconds
CONVERSATION_PROMPT = VOICE_CONFIG.conversation_prompt
HOTWORD_PROMPT = VOICE_CONFIG.hotword_prompt
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

HOTKEY_NAME = VOICE_CONFIG.hotkey_name
HOTKEY_VK = VOICE_CONFIG.hotkey_vk
TOGGLE_LISTENING_HOTKEY_NAME = VOICE_CONFIG.toggle_listening_hotkey_name
TOGGLE_LISTENING_HOTKEY_VK = VOICE_CONFIG.toggle_listening_hotkey_vk
SPEECH_INTERRUPT_KEYS = VOICE_CONFIG.speech_interrupt_keys


def _audio_capture_config():
    return VOICE_CONFIG.audio_capture_config()


@dataclass
class VoiceResult:
    ok: bool
    text: str = ""
    error: str = ""
    command_text: str = ""


def _get_model(model_size: str):
    return _get_model_core(model_size)


def _chunk_levels(chunk: np.ndarray) -> tuple[float, float]:
    return _chunk_levels_core(chunk)


def _chunk_has_speech(chunk: np.ndarray, threshold: float) -> bool:
    return _chunk_has_speech_core(chunk, threshold)


def list_input_devices() -> list[dict]:
    return _list_input_devices_core(SAMPLE_RATE)


def _resolve_input_device() -> tuple[int | None, dict | None]:
    return _resolve_input_device_core(load_voice_preferences(), device_loader=list_input_devices)


def get_active_input_device_info() -> dict | None:
    _index, device = _resolve_input_device()
    return device


def format_input_devices() -> str:
    devices = list_input_devices()
    active = get_active_input_device_info()
    return _format_input_devices_core(devices, active)


def _preprocess_audio(audio: np.ndarray) -> np.ndarray:
    return _preprocess_audio_core(audio, _audio_capture_config())


def _record_audio(
    timeout_seconds: float,
    min_speech_seconds: float = DEFAULT_MIN_SPEECH_SECONDS,
    max_silence_seconds: float = DEFAULT_MAX_SILENCE_SECONDS,
) -> np.ndarray:
    return _record_audio_core(
        timeout_seconds,
        min_speech_seconds,
        max_silence_seconds,
        _audio_capture_config(),
        _resolve_input_device,
    )


def _record_fixed_audio(duration_seconds: float) -> np.ndarray:
    return _record_fixed_audio_core(duration_seconds, _audio_capture_config(), _resolve_input_device)


def _audio_has_signal(audio: np.ndarray) -> bool:
    return _audio_has_signal_core(audio, _audio_capture_config())


def _is_prompt_hallucination(text: str) -> bool:
    return _recognition_is_prompt_hallucination(text)



def _extract_inline_command(text: str, hotword: str) -> str:
    return _recognition_extract_inline_command(text, hotword)



def _save_temp_wav(audio: np.ndarray) -> str:
    return _save_temp_wav_core(audio, SAMPLE_RATE)


def _save_wav(path: str | Path, audio: np.ndarray):
    _save_wav_core(path, audio, SAMPLE_RATE)


def _format_audio_stats(label: str, audio: np.ndarray) -> str:
    return _format_audio_stats_core(label=label, audio=audio, sample_rate=SAMPLE_RATE, chunk_levels=_chunk_levels)


def run_audio_diagnostic(seconds: float | None = None) -> str:
    return _run_audio_diagnostic_core(
        seconds=seconds,
        default_seconds=AUDIO_DIAGNOSTIC_SECONDS,
        sample_rate=SAMPLE_RATE,
        command_model_size=COMMAND_MODEL_SIZE,
        command_prompt=COMMAND_PROMPT,
        whisper_command_beam_size=WHISPER_COMMAND_BEAM_SIZE,
        whisper_command_best_of=WHISPER_COMMAND_BEST_OF,
        whisper_command_vad_filter=WHISPER_COMMAND_VAD_FILTER,
        active_input_device_info=get_active_input_device_info,
        record_fixed_audio=_record_fixed_audio,
        preprocess_audio=_preprocess_audio,
        save_wav=_save_wav,
        transcribe_audio=_transcribe_audio,
        chunk_levels=_chunk_levels,
    )

def _transcribe_audio(
    audio: np.ndarray,
    model_size: str,
    prompt: str | None,
    beam_size: int,
    best_of: int,
    vad_filter: bool,
    preprocess: bool = True,
) -> VoiceResult:
    result = _transcribe_audio_core(
        audio=audio,
        model_size=model_size,
        prompt=prompt,
        beam_size=beam_size,
        best_of=best_of,
        vad_filter=vad_filter,
        preprocess=preprocess,
        config=WhisperTranscriptionConfig(
            command_model_size=COMMAND_MODEL_SIZE,
            command_prompt=COMMAND_PROMPT,
            command_rescue_prompt=COMMAND_RESCUE_PROMPT,
        ),
        audio_has_signal=_audio_has_signal,
        preprocess_audio=_preprocess_audio,
        save_temp_wav=_save_temp_wav,
        get_model=_get_model,
        resolve_transcription_text=_resolve_transcription_text_core,
        is_prompt_hallucination=_is_prompt_hallucination,
        should_retry_command_transcription=_should_retry_command_transcription,
        command_transcription_score=_command_transcription_score,
    )
    return VoiceResult(ok=result.ok, text=result.text, error=result.error)


def _contains_hotword(text: str, hotword: str) -> bool:
    return _recognition_contains_hotword(text, hotword)


def _command_transcription_plan():
    return _command_transcription_plan_core(
        command_model_size=COMMAND_MODEL_SIZE,
        command_prompt=COMMAND_PROMPT,
        whisper_command_beam_size=WHISPER_COMMAND_BEAM_SIZE,
        whisper_command_best_of=WHISPER_COMMAND_BEST_OF,
        whisper_command_vad_filter=WHISPER_COMMAND_VAD_FILTER,
    )


def _hotword_listen_plan():
    return _hotword_listen_plan_core(
        timeout_seconds=HOTWORD_TIMEOUT_SECONDS,
        min_speech_seconds=HOTWORD_MIN_SPEECH_SECONDS,
        max_silence_seconds=HOTWORD_MAX_SILENCE_SECONDS,
    )


def _hotword_transcription_plan():
    return _hotword_transcription_plan_core(
        hotword_model_size=HOTWORD_MODEL_SIZE,
        hotword_prompt=HOTWORD_PROMPT,
        whisper_hotword_beam_size=WHISPER_HOTWORD_BEAM_SIZE,
        whisper_hotword_best_of=WHISPER_HOTWORD_BEST_OF,
        whisper_hotword_vad_filter=WHISPER_HOTWORD_VAD_FILTER,
    )


def _conversation_listen_plan(timeout_seconds: float | None):
    return _conversation_listen_plan_core(
        requested_timeout_seconds=timeout_seconds,
        default_timeout_seconds=CONVERSATION_TIMEOUT_SECONDS,
        min_speech_seconds=CONVERSATION_MIN_SPEECH_SECONDS,
        max_silence_seconds=CONVERSATION_MAX_SILENCE_SECONDS,
    )


def _conversation_transcription_plan():
    return _conversation_transcription_plan_core(
        conversation_model_size=CONVERSATION_MODEL_SIZE,
        conversation_prompt=CONVERSATION_PROMPT,
        whisper_conversation_beam_size=WHISPER_CONVERSATION_BEAM_SIZE,
        whisper_conversation_best_of=WHISPER_CONVERSATION_BEST_OF,
        whisper_conversation_vad_filter=WHISPER_CONVERSATION_VAD_FILTER,
    )



def _consume_key_press(vk_code: int) -> bool:
    return _consume_key_press_core(vk_code)


def consume_hotkey_press() -> bool:
    return _consume_key_press(HOTKEY_VK)


def consume_toggle_listening_hotkey_press() -> bool:
    return _consume_key_press(TOGGLE_LISTENING_HOTKEY_VK)


def speech_interrupt_pressed() -> bool:
    return any(_consume_key_press(vk_code) for vk_code in SPEECH_INTERRUPT_KEYS)


def play_activation_sound():
    _play_activation_sound_core(VOICE_PREFERENCES)


def _clamp_int(value, minimum: int, maximum: int, default: int) -> int:
    return _clamp_int_core(value, minimum, maximum, default)


def _load_tts_pronunciations() -> dict[str, str]:
    return _load_tts_pronunciations_core(VOICE_PREFERENCES, TTS_PRONUNCIATIONS_PATH)


def _prepare_tts_text(text: str) -> str:
    return _prepare_tts_text_core(text, _load_tts_pronunciations())


def _wait_for_wav_playback(path: str | Path) -> VoiceResult | None:
    result = _wait_for_wav_playback_result_core(path, speech_interrupt_pressed)
    if result:
        return VoiceResult(ok=result.ok, text=result.text, error=result.error)
    return None


def _play_wav(path: str | Path) -> VoiceResult | None:
    result = _play_wav_result_core(
        path,
        preferences=VOICE_PREFERENCES,
        interrupt_pressed=speech_interrupt_pressed,
        wait_for_playback=_TTS_WAIT_FOR_PLAYBACK_OVERRIDE,
    )
    if result:
        return VoiceResult(ok=result.ok, text=result.text, error=result.error)
    return None


def _play_wav_chunk(path: str | Path) -> VoiceResult | None:
    result = _play_wav_chunk_result_core(path, speech_interrupt_pressed)
    if result:
        return VoiceResult(ok=result.ok, text=result.text, error=result.error)
    return None


def _apply_jarvis_audio_effect(path: str):
    _apply_jarvis_audio_effect_core(path, VOICE_PREFERENCES)


def _piper_tts_settings():
    return _piper_tts_settings_core(VOICE_PREFERENCES)


def _validated_piper_model(settings) -> VoiceResult | Path:
    validation = _validate_piper_tts_settings_core(settings)
    if validation.error:
        return VoiceResult(ok=False, error=validation.error)
    return validation.model


def _run_piper_synthesis(
    text_for_tts: str,
    output_path: str,
    settings,
    model: Path,
) -> VoiceResult | None:
    result = _run_piper_synthesis_core(
        text_for_tts,
        output_path,
        settings,
        model,
        preferences=VOICE_PREFERENCES,
        interrupt_pressed=speech_interrupt_pressed,
    )
    if result:
        return VoiceResult(ok=False, error=result.error)
    return None


def prime_piper_cache(phrases: list[str]) -> VoiceResult:
    settings = _piper_tts_settings()

    model = _validated_piper_model(settings)
    if isinstance(model, VoiceResult):
        return model

    result = _prime_piper_cache_runtime_core(
        phrases,
        settings=settings,
        model=model,
        preferences=VOICE_PREFERENCES,
        prepare_tts_text=_prepare_tts_text,
        apply_audio_effect=_apply_jarvis_audio_effect,
    )
    return VoiceResult(ok=result.ok, text=result.text, error=result.error)


def _speak_with_piper(text: str) -> VoiceResult:
    settings = _piper_tts_settings()

    model = _validated_piper_model(settings)
    if isinstance(model, VoiceResult):
        return model

    result = _speak_with_piper_runtime_core(
        text,
        settings=settings,
        model=model,
        preferences=VOICE_PREFERENCES,
        prepare_tts_text=_prepare_tts_text,
        run_piper_synthesis=_run_piper_synthesis,
        play_wav=_play_wav,
        play_wav_chunk=_play_wav_chunk,
    )
    return VoiceResult(ok=result.ok, text=result.text, error=result.error)


def _speak_with_gemini(text: str) -> VoiceResult:
    result = _speak_with_gemini_runtime_core(
        text,
        preferences=VOICE_PREFERENCES,
        prepare_tts_text=_prepare_tts_text,
        int_pref=_int_pref,
        interrupt_pressed=speech_interrupt_pressed,
        wait_for_playback=_TTS_WAIT_FOR_PLAYBACK_OVERRIDE,
    )
    return VoiceResult(ok=result.ok, text=result.text, error=result.error)


def _speak_with_windows(text: str, culture: str | None = None) -> VoiceResult:
    result = _speak_with_windows_runtime_core(
        text,
        culture=culture,
        preferences=VOICE_PREFERENCES,
        powershell_exe=POWERSHELL_EXE,
        interrupt_pressed=speech_interrupt_pressed,
    )
    return VoiceResult(ok=result.ok, text=result.text, error=result.error)


def listen_for_hotword(hotword: str = HOTWORD) -> VoiceResult:
    result = _listen_for_hotword_core(
        hotword=hotword,
        listen_plan=_hotword_listen_plan(),
        hotword_plan=_hotword_transcription_plan(),
        command_plan=_command_transcription_plan(),
        record_audio=_record_audio,
        transcribe_audio=_transcribe_audio,
        resolve_hotword_detection=_resolve_hotword_detection_core,
        contains_hotword=_contains_hotword,
        extract_inline_command=_extract_inline_command,
    )
    if result.ok:
        return VoiceResult(
            ok=True,
            text=result.text,
            command_text=result.command_text,
        )

    return VoiceResult(ok=False, error=result.error)


def listen_once(timeout_seconds: int = 6, culture: str = "pt") -> VoiceResult:
    del culture
    result = _listen_once_core(
        timeout_seconds=timeout_seconds,
        transcription_plan=_command_transcription_plan(),
        record_audio=_record_audio,
        transcribe_audio=_transcribe_audio,
    )
    return VoiceResult(ok=result.ok, text=result.text, error=result.error)


def listen_conversation_once(timeout_seconds: float | None = None, culture: str = "pt") -> VoiceResult:
    del culture
    result = _listen_conversation_once_core(
        listen_plan=_conversation_listen_plan(timeout_seconds),
        transcription_plan=_conversation_transcription_plan(),
        record_audio=_record_audio,
        transcribe_audio=_transcribe_audio,
    )
    return VoiceResult(ok=result.ok, text=result.text, error=result.error)


def speak(
    text: str,
    culture: str | None = None,
    *,
    interrupt_current: bool = False,
    wait_for_playback: bool | None = None,
) -> VoiceResult:
    global _TTS_WAIT_FOR_PLAYBACK_OVERRIDE

    if not text:
        return VoiceResult(ok=False, error="Nada para falar.")

    if not bool(VOICE_PREFERENCES.get("tts_enabled", True)):
        return VoiceResult(ok=True, text=text)

    previous_wait_override = _TTS_WAIT_FOR_PLAYBACK_OVERRIDE
    _TTS_WAIT_FOR_PLAYBACK_OVERRIDE = wait_for_playback

    if interrupt_current:
        try:
            _stop_playback_core()
        except Exception:
            pass

    try:
        return _speak_with_tts_routing_core(
            text,
            culture,
            VOICE_PREFERENCES,
            _speak_with_gemini,
            _speak_with_piper,
            _speak_with_windows,
        )
    finally:
        _TTS_WAIT_FOR_PLAYBACK_OVERRIDE = previous_wait_override
