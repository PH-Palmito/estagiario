import ctypes
import msvcrt
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from threading import Lock

import numpy as np

from llm.gemini_tts_client import synthesize_gemini_tts_to_wav
from memory.voice_preferences import load_voice_preferences
from voice.audio_capture import (
    AudioCaptureConfig,
)
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
from voice.audio_effects import (
    apply_jarvis_audio_effect as _apply_jarvis_audio_effect_core,
)
from voice.audio_effects import (
    voice_effect_strength as _voice_effect_strength_core,
)
from voice.audio_files import (
    save_temp_wav as _save_temp_wav_core,
)
from voice.audio_files import (
    save_wav as _save_wav_core,
)
from voice.audio_files import (
    tts_cache_path as _tts_cache_path_core,
)
from voice.audio_files import (
    wav_duration_seconds as _wav_duration_seconds_core,
)
from voice.audio_files import (
    write_raw_pcm_to_wav as _write_raw_pcm_to_wav_core,
)
from voice.audio_playback import (
    play_wav as _play_wav_core,
)
from voice.audio_playback import (
    play_wav_chunk as _play_wav_chunk_core,
)
from voice.audio_playback import (
    stop_playback as _stop_playback_core,
)
from voice.audio_playback import (
    wait_for_wav_playback as _wait_for_wav_playback_core,
)
from voice.gemini_tts_utils import gemini_tts_plan as _gemini_tts_plan_core
from voice.hotkeys import (
    consume_key_press as _consume_key_press_core,
)
from voice.hotkeys import (
    hotkey_name as _hotkey_name_core,
)
from voice.hotkeys import (
    hotkey_vk as _hotkey_vk_core,
)
from voice.hotkeys import (
    play_activation_sound as _play_activation_sound_core,
)
from voice.hotkeys import (
    speech_interrupt_keys as _speech_interrupt_keys_core,
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
from voice.piper_utils import (
    load_piper_sample_rate as _load_piper_sample_rate_core,
)
from voice.piper_utils import (
    piper_cache_settings as _piper_cache_settings_core,
)
from voice.piper_utils import (
    piper_cli_command as _piper_cli_command_core,
)
from voice.piper_utils import (
    piper_synthesis_plan as _piper_synthesis_plan_core,
)
from voice.piper_utils import (
    piper_tts_settings as _piper_tts_settings_core,
)
from voice.piper_utils import (
    piper_worker_command as _piper_worker_command_core,
)
from voice.piper_utils import (
    piper_worker_payload as _piper_worker_payload_core,
)
from voice.piper_utils import (
    piper_worker_read_size as _piper_worker_read_size_core,
)
from voice.piper_utils import (
    piper_worker_runtime_settings as _piper_worker_runtime_settings_core,
)
from voice.piper_utils import (
    piper_worker_signature as _piper_worker_signature_core,
)
from voice.piper_utils import (
    read_piper_worker_audio_loop as _read_piper_worker_audio_loop_core,
)
from voice.piper_utils import (
    validate_piper_tts_settings as _validate_piper_tts_settings_core,
)
from voice.piper_utils import (
    write_piper_worker_payload as _write_piper_worker_payload_core,
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
from voice.tts_routing import speak_with_tts_routing as _speak_with_tts_routing_core
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
from voice.windows_tts import monitor_windows_tts_process as _monitor_windows_tts_process_core
from voice.windows_tts import (
    windows_tts_error as _windows_tts_error_core,
)
from voice.windows_tts import (
    windows_tts_plan as _windows_tts_plan_core,
)

POWERSHELL_EXE = "powershell"
kernel32 = ctypes.windll.kernel32
SAMPLE_RATE = 16000
COMMAND_MODEL_SIZE = "small"
HOTWORD_MODEL_SIZE = "tiny"
FRAME_SIZE = 1024
DEFAULT_MAX_RECORD_SECONDS = 6.0
VOICE_PREFERENCES = load_voice_preferences()
CONVERSATION_MODEL_SIZE = str(VOICE_PREFERENCES.get("conversation_model_size", COMMAND_MODEL_SIZE))
TTS_PRONUNCIATIONS_PATH = Path("memory") / "tts_pronunciations.json"
_PIPER_WORKER_LOCK = Lock()
_PIPER_WORKER_PROCESS = None
_PIPER_WORKER_SIGNATURE = None
_PIPER_WORKER_SAMPLE_RATE = 22050
_PIPER_WORKER_WARM = False
_TTS_WAIT_FOR_PLAYBACK_OVERRIDE = None


def _float_pref(name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(VOICE_PREFERENCES.get(name, default))
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, value))


def _int_pref(name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(VOICE_PREFERENCES.get(name, default))
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, value))


DEFAULT_MIN_SPEECH_SECONDS = _float_pref("audio_min_speech_seconds", 0.25, 0.05, 2.0)
DEFAULT_MAX_SILENCE_SECONDS = _float_pref("audio_max_silence_seconds", 0.75, 0.2, 3.0)
SILENCE_THRESHOLD = _float_pref("audio_silence_threshold", 0.01, 0.001, 0.2)
AUDIO_DYNAMIC_THRESHOLD = bool(VOICE_PREFERENCES.get("audio_dynamic_threshold", True))
AUDIO_NOISE_MULTIPLIER = _float_pref("audio_noise_multiplier", 3.0, 1.2, 10.0)
AUDIO_MAX_DYNAMIC_THRESHOLD = _float_pref("audio_max_dynamic_threshold", 0.04, 0.005, 0.3)
AUDIO_PREROLL_SECONDS = _float_pref("audio_preroll_seconds", 0.25, 0.0, 1.0)
AUDIO_NORMALIZE_ENABLED = bool(VOICE_PREFERENCES.get("audio_normalize_enabled", True))
AUDIO_DC_OFFSET_FILTER = bool(VOICE_PREFERENCES.get("audio_dc_offset_filter", True))
AUDIO_TARGET_PEAK = _float_pref("audio_target_peak", 0.75, 0.1, 0.98)
AUDIO_MAX_GAIN = _float_pref("audio_max_gain", 4.0, 1.0, 20.0)
AUDIO_DIAGNOSTIC_SECONDS = _float_pref("audio_diagnostic_seconds", 4.0, 1.0, 15.0)
WHISPER_COMMAND_VAD_FILTER = bool(VOICE_PREFERENCES.get("whisper_command_vad_filter", False))
WHISPER_CONVERSATION_VAD_FILTER = bool(VOICE_PREFERENCES.get("whisper_conversation_vad_filter", False))
WHISPER_HOTWORD_VAD_FILTER = bool(VOICE_PREFERENCES.get("whisper_hotword_vad_filter", True))
WHISPER_COMMAND_BEAM_SIZE = _int_pref("whisper_command_beam_size", 5, 1, 10)
WHISPER_COMMAND_BEST_OF = _int_pref("whisper_command_best_of", 5, 1, 10)
WHISPER_CONVERSATION_BEAM_SIZE = _int_pref("whisper_conversation_beam_size", 3, 1, 10)
WHISPER_CONVERSATION_BEST_OF = _int_pref("whisper_conversation_best_of", 3, 1, 10)
WHISPER_HOTWORD_BEAM_SIZE = _int_pref("whisper_hotword_beam_size", 1, 1, 5)
WHISPER_HOTWORD_BEST_OF = _int_pref("whisper_hotword_best_of", 1, 1, 5)
HOTWORD = str(VOICE_PREFERENCES.get("hotword", "estagiario"))
HOTWORD_LISTENING_ENABLED = bool(VOICE_PREFERENCES.get("hotword_listening_enabled", False))
HOTWORD_TIMEOUT_SECONDS = _float_pref("hotword_timeout_seconds", 3.0, 0.8, 8.0)
HOTWORD_MAX_SILENCE_SECONDS = _float_pref("hotword_max_silence_seconds", 0.5, 0.15, 2.0)
HOTWORD_MIN_SPEECH_SECONDS = _float_pref("hotword_min_speech_seconds", 0.12, 0.05, 1.0)
CONVERSATION_TIMEOUT_SECONDS = _float_pref("conversation_timeout_seconds", 7.0, 1.0, 12.0)
CONVERSATION_MAX_SILENCE_SECONDS = _float_pref("conversation_max_silence_seconds", 1.0, 0.25, 3.0)
CONVERSATION_MIN_SPEECH_SECONDS = _float_pref("conversation_min_speech_seconds", 0.35, 0.08, 2.0)
COMMAND_PROMPT = (
    "Comandos curtos em portugues do Brasil para controlar o computador. "
    "Transcreva sempre em portugues do Brasil, nunca em ingles. "
    "Verbos comuns: abrir, fechar, focar, trocar, minimizar, maximizar, restaurar, pesquisar, ler, selecionar. "
    "Comandos de musica: tocar algo alegre, tocar algo calmo, tocar rock, tocar classico, me surpreenda, "
    "adicionar na fila, tocar musicas curtidas, tocar filho meu, tocar blindado no Spotify. "
    "Alvos comuns: chrome, youtube, google, vscode, code, spotify, whatsapp, zap, bloco de notas, "
    "powershell, edge, github, android studio, steam, mercado livre, magalu."
)
COMMAND_RESCUE_PROMPT = (
    "Transcreva apenas em portugues do Brasil. "
    "Nao invente palavras em ingles. "
    "Priorize comandos curtos e simples. "
    "Exemplos provaveis: o que tem na tela, resuma a tela, detalha a tela, "
    "abrir youtube, abrir chrome, abrir spotify, fechar spotify, "
    "tocar algo alegre, tocar algo calmo, tocar rock, tocar filho meu, tocar blindado no Spotify, me surpreenda, adicionar na fila, "
    "pesquisar notebook no mercado livre, abrir github, abrir whatsapp."
)
CONVERSATION_PROMPT = str(
    VOICE_PREFERENCES.get(
        "conversation_transcription_prompt",
        "Conversa casual em portugues do Brasil.",
    )
).strip()
HOTWORD_PROMPT = f"Palavra de ativacao: {HOTWORD}."
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

HOTKEY_NAME = _hotkey_name_core(VOICE_PREFERENCES, "trigger_hotkey", "F8")
HOTKEY_VK = _hotkey_vk_core(HOTKEY_NAME, "F8")
TOGGLE_LISTENING_HOTKEY_NAME = _hotkey_name_core(VOICE_PREFERENCES, "toggle_listening_hotkey", "F9")
TOGGLE_LISTENING_HOTKEY_VK = _hotkey_vk_core(TOGGLE_LISTENING_HOTKEY_NAME, "F9")
SPEECH_INTERRUPT_KEYS = _speech_interrupt_keys_core(HOTKEY_VK, TOGGLE_LISTENING_HOTKEY_VK)


def _audio_capture_config() -> AudioCaptureConfig:
    return AudioCaptureConfig(
        sample_rate=SAMPLE_RATE,
        frame_size=FRAME_SIZE,
        default_max_record_seconds=DEFAULT_MAX_RECORD_SECONDS,
        silence_threshold=SILENCE_THRESHOLD,
        audio_dynamic_threshold=AUDIO_DYNAMIC_THRESHOLD,
        audio_noise_multiplier=AUDIO_NOISE_MULTIPLIER,
        audio_max_dynamic_threshold=AUDIO_MAX_DYNAMIC_THRESHOLD,
        audio_preroll_seconds=AUDIO_PREROLL_SECONDS,
        audio_normalize_enabled=AUDIO_NORMALIZE_ENABLED,
        audio_dc_offset_filter=AUDIO_DC_OFFSET_FILTER,
        audio_target_peak=AUDIO_TARGET_PEAK,
        audio_max_gain=AUDIO_MAX_GAIN,
    )


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
    peak, rms = _chunk_levels(audio)
    duration = audio.size / SAMPLE_RATE if audio.size else 0.0
    return f"{label}: duracao={duration:.2f}s pico={peak:.4f} rms={rms:.4f}"


def run_audio_diagnostic(seconds: float | None = None) -> str:
    duration = seconds if seconds is not None else AUDIO_DIAGNOSTIC_SECONDS
    duration = max(1.0, min(15.0, float(duration)))
    active_device = get_active_input_device_info()

    try:
        raw_audio = _record_fixed_audio(duration)
    except Exception as exc:
        return f"Falha ao gravar diagnostico de audio: {exc}"

    processed_audio = _preprocess_audio(raw_audio)
    output_dir = Path("memory") / "audio_diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = output_dir / f"audio_raw_{stamp}.wav"
    processed_path = output_dir / f"audio_processed_{stamp}.wav"

    _save_wav(raw_path, raw_audio)
    _save_wav(processed_path, processed_audio)
    raw_transcription = _transcribe_audio(
        raw_audio,
        model_size=COMMAND_MODEL_SIZE,
        prompt=COMMAND_PROMPT,
        beam_size=WHISPER_COMMAND_BEAM_SIZE,
        best_of=WHISPER_COMMAND_BEST_OF,
        vad_filter=WHISPER_COMMAND_VAD_FILTER,
        preprocess=False,
    )
    processed_transcription = _transcribe_audio(
        processed_audio,
        model_size=COMMAND_MODEL_SIZE,
        prompt=COMMAND_PROMPT,
        beam_size=WHISPER_COMMAND_BEAM_SIZE,
        best_of=WHISPER_COMMAND_BEST_OF,
        vad_filter=WHISPER_COMMAND_VAD_FILTER,
        preprocess=False,
    )
    raw_text = raw_transcription.text if raw_transcription.ok else raw_transcription.error
    processed_text = processed_transcription.text if processed_transcription.ok else processed_transcription.error

    return "\n".join(
        [
            "Diagnostico de audio concluido.",
            (
                f"Microfone usado: {active_device['name']}"
                if active_device
                else "Microfone usado: padrão do Windows"
            ),
            _format_audio_stats("Bruto", raw_audio),
            _format_audio_stats("Processado", processed_audio),
            f"Whisper bruto: {raw_text}",
            f"Whisper processado: {processed_text}",
            f"Arquivo bruto: {raw_path.resolve()}",
            f"Arquivo processado: {processed_path.resolve()}",
        ]
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
    if not _audio_has_signal(audio):
        return VoiceResult(ok=False, error="Nao detectei fala no microfone.")

    def _transcribe_once(active_prompt: str | None, active_beam: int, active_best_of: int, active_vad: bool):
        processed_audio = _preprocess_audio(audio) if preprocess else audio
        active_temp_path = _save_temp_wav(processed_audio)
        try:
            model = _get_model(model_size)
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
        text, info = _transcribe_once(prompt, beam_size, best_of, vad_filter)

        resolution = _resolve_transcription_text_core(
            text,
            model_size=model_size,
            command_model_size=COMMAND_MODEL_SIZE,
            prompt=prompt,
            command_prompt=COMMAND_PROMPT,
            command_rescue_prompt=COMMAND_RESCUE_PROMPT,
            beam_size=beam_size,
            best_of=best_of,
            prompt_hallucination_error="Nao captei com precisao.",
            transcribe_once=_transcribe_once,
            is_prompt_hallucination=_is_prompt_hallucination,
            should_retry_command_transcription=_should_retry_command_transcription,
            command_transcription_score=_command_transcription_score,
        )
        if not resolution.ok:
            return VoiceResult(ok=False, error=resolution.error)
        text = resolution.text

        if info.language_probability is not None and info.language_probability < 0.25:
            return VoiceResult(ok=True, text=text)

        return VoiceResult(ok=True, text=text)
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao transcrever audio: {exc}")


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


def _wav_duration_seconds(path: str | Path) -> float:
    return _wav_duration_seconds_core(path)


def _tts_cache_path(engine: str, text: str, settings: list[str]) -> Path:
    return _tts_cache_path_core(engine, text, settings)


def _load_piper_sample_rate(config_path: str) -> int:
    return _load_piper_sample_rate_core(config_path)


def _piper_worker_signature(
    piper_exe: str,
    model_path: str,
    config_path: str,
    speaker_id: str,
    length_scale: str,
    noise_scale: str,
    noise_w: str,
) -> tuple[str, ...]:
    return _piper_worker_signature_core(
        piper_exe,
        model_path,
        config_path,
        speaker_id,
        length_scale,
        noise_scale,
        noise_w,
    )


def _stop_piper_worker_locked():
    global _PIPER_WORKER_PROCESS, _PIPER_WORKER_SIGNATURE, _PIPER_WORKER_WARM

    process = _PIPER_WORKER_PROCESS
    _PIPER_WORKER_PROCESS = None
    _PIPER_WORKER_SIGNATURE = None
    _PIPER_WORKER_WARM = False

    if not process:
        return

    try:
        if process.stdin:
            try:
                process.stdin.close()
            except Exception:
                pass
        process.terminate()
        process.wait(timeout=1.5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def _ensure_piper_worker(
    settings,
    model_path: str,
):
    global _PIPER_WORKER_PROCESS, _PIPER_WORKER_SIGNATURE, _PIPER_WORKER_SAMPLE_RATE, _PIPER_WORKER_WARM

    signature = _piper_worker_signature(
        settings.piper_exe,
        model_path,
        settings.config_path,
        settings.speaker_id,
        settings.length_scale,
        settings.noise_scale,
        settings.noise_w,
    )

    with _PIPER_WORKER_LOCK:
        process = _PIPER_WORKER_PROCESS
        if (
            process is not None
            and process.poll() is None
            and signature == _PIPER_WORKER_SIGNATURE
        ):
            return process

        _stop_piper_worker_locked()

        command = _piper_worker_command_core(settings, model_path)

        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        _PIPER_WORKER_PROCESS = process
        _PIPER_WORKER_SIGNATURE = signature
        _PIPER_WORKER_SAMPLE_RATE = _load_piper_sample_rate(settings.config_path)
        _PIPER_WORKER_WARM = False
        return process


def _piper_stdout_available(stdout) -> int:
    try:
        handle = msvcrt.get_osfhandle(stdout.fileno())
        total_available = ctypes.c_ulong(0)
        ok = kernel32.PeekNamedPipe(
            ctypes.c_void_p(handle),
            None,
            0,
            None,
            ctypes.byref(total_available),
            None,
        )
        return int(total_available.value) if ok else 0
    except Exception:
        return 0


def _read_piper_stdout_chunk(stdout) -> bytes | None:
    read_size = _piper_worker_read_size_core(_piper_stdout_available(stdout))
    if read_size <= 0:
        return b""

    try:
        return os.read(stdout.fileno(), read_size)
    except Exception:
        return None


def _read_piper_worker_audio(process, timeout_seconds: float, idle_seconds: float):
    global _PIPER_WORKER_WARM

    result = _read_piper_worker_audio_loop_core(
        process,
        timeout_seconds=timeout_seconds,
        idle_seconds=idle_seconds,
        worker_warm=_PIPER_WORKER_WARM,
        interrupt_pressed=speech_interrupt_pressed,
        stop_worker=_stop_piper_worker_locked,
        read_stdout_chunk=_read_piper_stdout_chunk,
        monotonic=time.monotonic,
        sleep=time.sleep,
    )
    _PIPER_WORKER_WARM = result.worker_warm
    if result.error:
        return VoiceResult(ok=False, error=result.error), result.audio_bytes
    return None, result.audio_bytes


def _write_raw_pcm_to_wav(output_path: str, audio_bytes: bytes, sample_rate: int):
    _write_raw_pcm_to_wav_core(output_path, audio_bytes, sample_rate)


def _wait_for_wav_playback(path: str | Path) -> VoiceResult | None:
    if _wait_for_wav_playback_core(path, _wav_duration_seconds, speech_interrupt_pressed):
        return VoiceResult(ok=False, error="Fala interrompida.")
    return None


def _play_wav(path: str | Path) -> VoiceResult | None:
    wait_for_playback = _TTS_WAIT_FOR_PLAYBACK_OVERRIDE
    if wait_for_playback is None:
        wait_for_playback = bool(VOICE_PREFERENCES.get("tts_wait_for_playback", True))

    if _play_wav_core(path, _wav_duration_seconds, speech_interrupt_pressed, wait_for_playback):
        return VoiceResult(ok=False, error="Fala interrompida.")
    return None


def _play_wav_chunk(path: str | Path) -> VoiceResult | None:
    if _play_wav_chunk_core(path, _wav_duration_seconds, speech_interrupt_pressed):
        return VoiceResult(ok=False, error="Fala interrompida.")
    return None


def _voice_effect_strength() -> float:
    return _voice_effect_strength_core(VOICE_PREFERENCES)


def _apply_jarvis_audio_effect(path: str):
    _apply_jarvis_audio_effect_core(path, VOICE_PREFERENCES)


def _piper_cache_settings(
    model_path: str,
    config_path: str,
    speaker_id: str,
    length_scale: str,
    noise_scale: str,
    noise_w: str,
) -> list[str]:
    return _piper_cache_settings_core(
        model_path,
        config_path,
        speaker_id,
        length_scale,
        noise_scale,
        noise_w,
        VOICE_PREFERENCES,
    )


def _piper_synthesis_plan(text_for_tts: str, cache_settings: list[str]):
    return _piper_synthesis_plan_core(text_for_tts, cache_settings, VOICE_PREFERENCES)


def _piper_tts_settings():
    return _piper_tts_settings_core(VOICE_PREFERENCES)


def _piper_worker_runtime_settings():
    return _piper_worker_runtime_settings_core(VOICE_PREFERENCES)


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
    worker_settings = _piper_worker_runtime_settings()

    if worker_settings.enabled:
        try:
            process = _ensure_piper_worker(
                settings,
                str(model),
            )

            payload = _piper_worker_payload_core(text_for_tts)

            with _PIPER_WORKER_LOCK:
                _write_piper_worker_payload_core(process, payload)

            interrupt_result, audio_bytes = _read_piper_worker_audio(
                process,
                timeout_seconds=worker_settings.timeout_seconds,
                idle_seconds=worker_settings.idle_seconds,
            )

            if interrupt_result:
                return interrupt_result

            if audio_bytes:
                _write_raw_pcm_to_wav(output_path, audio_bytes, _PIPER_WORKER_SAMPLE_RATE)
                _apply_jarvis_audio_effect(output_path)
                return None

            with _PIPER_WORKER_LOCK:
                _stop_piper_worker_locked()

        except Exception as exc:
            with _PIPER_WORKER_LOCK:
                _stop_piper_worker_locked()

            if not worker_settings.fallback_to_cli:
                return VoiceResult(ok=False, error=f"Worker persistente do Piper falhou: {exc}")

        if not worker_settings.fallback_to_cli:
            return VoiceResult(ok=False, error="Worker persistente do Piper falhou.")

    command = _piper_cli_command_core(settings, str(model), output_path)

    try:
        completed = subprocess.run(
            command,
            input=text_for_tts,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except FileNotFoundError:
        return VoiceResult(ok=False, error=f"Piper nao encontrado: {settings.piper_exe}")
    except subprocess.TimeoutExpired:
        return VoiceResult(ok=False, error="Tempo limite atingido ao falar com Piper.")
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao usar Piper: {exc}")

    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "").strip()
        return VoiceResult(ok=False, error=error or "Piper nao conseguiu gerar audio.")

    _apply_jarvis_audio_effect(output_path)
    return None


def prime_piper_cache(phrases: list[str]) -> VoiceResult:
    settings = _piper_tts_settings()

    model = _validated_piper_model(settings)
    if isinstance(model, VoiceResult):
        return model

    warmed = 0
    skipped = 0
    errors = []

    for phrase in phrases:
        phrase = str(phrase).strip()
        if not phrase:
            continue

        text_for_tts = _prepare_tts_text(phrase)
        cache_path = _tts_cache_path(
            "piper",
            text_for_tts,
            _piper_cache_settings(
                str(model),
                settings.config_path,
                settings.speaker_id,
                settings.length_scale,
                settings.noise_scale,
                settings.noise_w,
            ),
        )
        if cache_path.exists():
            skipped += 1
            continue

        command = _piper_cli_command_core(settings, str(model), str(cache_path))

        try:
            completed = subprocess.run(
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

        _apply_jarvis_audio_effect(str(cache_path))
        warmed += 1

    if errors:
        return VoiceResult(
            ok=False,
            text=f"Cache TTS: {warmed} criado(s), {skipped} ja existia(m).",
            error=errors[0],
        )

    return VoiceResult(ok=True, text=f"Cache TTS: {warmed} criado(s), {skipped} ja existia(m).")


def _speak_with_piper(text: str) -> VoiceResult:
    text_for_tts = _prepare_tts_text(text)
    settings = _piper_tts_settings()

    model = _validated_piper_model(settings)
    if isinstance(model, VoiceResult):
        return model

    cache_settings = _piper_cache_settings(
        str(model),
        settings.config_path,
        settings.speaker_id,
        settings.length_scale,
        settings.noise_scale,
        settings.noise_w,
    )

    plan = _piper_synthesis_plan(text_for_tts, cache_settings)

    cache_path = None
    if plan.cache_enabled:
        cache_path = _tts_cache_path(
            "piper",
            plan.text,
            plan.cache_settings,
        )
        if cache_path.exists():
            interrupted = _play_wav(cache_path)
            if interrupted:
                return interrupted
            return VoiceResult(ok=True, text=text)

    if plan.should_chunk:
        for chunk_text in plan.chunks:
            chunk_cache_path = None
            if plan.cache_enabled:
                chunk_cache_path = _tts_cache_path("piper", chunk_text, plan.cache_settings)
                if chunk_cache_path.exists():
                    interrupted = _play_wav_chunk(chunk_cache_path)
                    if interrupted:
                        return interrupted
                    continue

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
                chunk_output_path = temp_file.name

            try:
                error_result = _run_piper_synthesis(
                    chunk_text,
                    chunk_output_path,
                    settings,
                    model,
                )
                if error_result:
                    return error_result

                play_path = chunk_output_path
                if chunk_cache_path:
                    shutil.copy2(chunk_output_path, chunk_cache_path)
                    play_path = str(chunk_cache_path)

                interrupted = _play_wav_chunk(play_path)
                if interrupted:
                    return interrupted
            finally:
                try:
                    Path(chunk_output_path).unlink(missing_ok=True)
                except Exception:
                    pass

        return VoiceResult(ok=True, text=text)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
        output_path = temp_file.name

    try:
        error_result = _run_piper_synthesis(
            plan.text,
            output_path,
            settings,
            model,
        )
        if error_result:
            return error_result
        play_path = output_path
        if cache_path:
            shutil.copy2(output_path, cache_path)
            play_path = str(cache_path)

        interrupted = _play_wav(play_path)
        if interrupted:
            return interrupted

        return VoiceResult(ok=True, text=text)
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass


def _speak_with_gemini(text: str) -> VoiceResult:
    text_for_tts = _prepare_tts_text(text)
    timeout_seconds = _int_pref("gemini_tts_timeout_seconds", 60, 10, 180)
    plan = _gemini_tts_plan_core(text_for_tts, VOICE_PREFERENCES, timeout_seconds)

    cache_path = None
    if plan.cache_enabled:
        cache_path = _tts_cache_path(
            "gemini",
            plan.text,
            plan.cache_settings,
        )
        if cache_path.exists():
            interrupted = _play_wav(cache_path)
            if interrupted:
                return interrupted
            return VoiceResult(ok=True, text=text)

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
        _apply_jarvis_audio_effect(output_path)

        play_path = output_path
        if cache_path:
            shutil.copy2(output_path, cache_path)
            play_path = str(cache_path)

        interrupted = _play_wav(play_path)
        if interrupted:
            return interrupted

        return VoiceResult(ok=True, text=text)
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Gemini TTS falhou: {exc}")
    finally:
        try:
            Path(output_path).unlink(missing_ok=True)
        except Exception:
            pass


def _speak_with_windows(text: str, culture: str | None = None) -> VoiceResult:
    plan = _windows_tts_plan_core(text, culture, VOICE_PREFERENCES, POWERSHELL_EXE)

    try:
        process = subprocess.Popen(
            plan.command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        monitor_result = _monitor_windows_tts_process_core(
            process,
            speech_interrupt_pressed,
            time.monotonic,
            time.sleep,
        )
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao iniciar voz sintetizada: {exc}")

    if monitor_result.error:
        return VoiceResult(ok=False, error=monitor_result.error)

    error = _windows_tts_error_core(monitor_result.completed)
    if error:
        return VoiceResult(ok=False, error=error)

    return VoiceResult(ok=True, text=text)


def listen_for_hotword(hotword: str = HOTWORD) -> VoiceResult:
    listen_plan = _hotword_listen_plan()
    hotword_plan = _hotword_transcription_plan()
    command_plan = _command_transcription_plan()

    try:
        audio = _record_audio(
            listen_plan.timeout_seconds,
            min_speech_seconds=listen_plan.min_speech_seconds,
            max_silence_seconds=listen_plan.max_silence_seconds,
        )
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao acessar o microfone: {exc}")

    result = _transcribe_audio(
        audio=audio,
        model_size=hotword_plan.model_size,
        prompt=hotword_plan.prompt,
        beam_size=hotword_plan.beam_size,
        best_of=hotword_plan.best_of,
        vad_filter=hotword_plan.vad_filter,
    )

    if not result.ok:
        return result

    def _transcribe_inline_command():
        return _transcribe_audio(
            audio=audio,
            model_size=command_plan.model_size,
            prompt=command_plan.prompt,
            beam_size=command_plan.beam_size,
            best_of=command_plan.best_of,
            vad_filter=command_plan.vad_filter,
        )

    hotword_resolution = _resolve_hotword_detection_core(
        hotword_text=result.text,
        hotword=hotword,
        contains_hotword=_contains_hotword,
        transcribe_command=_transcribe_inline_command,
        extract_inline_command=_extract_inline_command,
    )
    if hotword_resolution.ok:
        return VoiceResult(
            ok=True,
            text=hotword_resolution.text,
            command_text=hotword_resolution.command_text,
        )

    return VoiceResult(ok=False, error=hotword_resolution.error)


def listen_once(timeout_seconds: int = 6, culture: str = "pt") -> VoiceResult:
    del culture
    plan = _command_transcription_plan()

    try:
        audio = _record_audio(timeout_seconds)
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao acessar o microfone: {exc}")

    return _transcribe_audio(
        audio=audio,
        model_size=plan.model_size,
        prompt=plan.prompt,
        beam_size=plan.beam_size,
        best_of=plan.best_of,
        vad_filter=plan.vad_filter,
    )


def listen_conversation_once(timeout_seconds: float | None = None, culture: str = "pt") -> VoiceResult:
    del culture
    listen_plan = _conversation_listen_plan(timeout_seconds)
    transcription_plan = _conversation_transcription_plan()

    try:
        audio = _record_audio(
            listen_plan.timeout_seconds,
            min_speech_seconds=listen_plan.min_speech_seconds,
            max_silence_seconds=listen_plan.max_silence_seconds,
        )
    except Exception as exc:
        return VoiceResult(ok=False, error=f"Falha ao acessar o microfone: {exc}")

    return _transcribe_audio(
        audio=audio,
        model_size=transcription_plan.model_size,
        prompt=transcription_plan.prompt,
        beam_size=transcription_plan.beam_size,
        best_of=transcription_plan.best_of,
        vad_filter=transcription_plan.vad_filter,
    )


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
