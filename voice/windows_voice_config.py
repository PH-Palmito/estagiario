from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from voice.audio_capture import AudioCaptureConfig
from voice.hotkeys import hotkey_name, hotkey_vk, speech_interrupt_keys

SAMPLE_RATE = 16000
COMMAND_MODEL_SIZE = "small"
HOTWORD_MODEL_SIZE = "tiny"
FRAME_SIZE = 1024
DEFAULT_MAX_RECORD_SECONDS = 6.0
TTS_PRONUNCIATIONS_PATH = Path("memory") / "tts_pronunciations.json"

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


@dataclass(frozen=True)
class VoiceRuntimeConfig:
    conversation_model_size: str
    default_min_speech_seconds: float
    default_max_silence_seconds: float
    silence_threshold: float
    audio_dynamic_threshold: bool
    audio_noise_multiplier: float
    audio_max_dynamic_threshold: float
    audio_preroll_seconds: float
    audio_normalize_enabled: bool
    audio_dc_offset_filter: bool
    audio_target_peak: float
    audio_max_gain: float
    audio_diagnostic_seconds: float
    whisper_command_vad_filter: bool
    whisper_conversation_vad_filter: bool
    whisper_hotword_vad_filter: bool
    whisper_command_beam_size: int
    whisper_command_best_of: int
    whisper_conversation_beam_size: int
    whisper_conversation_best_of: int
    whisper_hotword_beam_size: int
    whisper_hotword_best_of: int
    hotword: str
    hotword_listening_enabled: bool
    hotword_timeout_seconds: float
    hotword_max_silence_seconds: float
    hotword_min_speech_seconds: float
    conversation_timeout_seconds: float
    conversation_max_silence_seconds: float
    conversation_min_speech_seconds: float
    conversation_prompt: str
    hotword_prompt: str
    hotkey_name: str
    hotkey_vk: int
    toggle_listening_hotkey_name: str
    toggle_listening_hotkey_vk: int
    speech_interrupt_keys: set[int]

    def audio_capture_config(self) -> AudioCaptureConfig:
        return AudioCaptureConfig(
            sample_rate=SAMPLE_RATE,
            frame_size=FRAME_SIZE,
            default_max_record_seconds=DEFAULT_MAX_RECORD_SECONDS,
            silence_threshold=self.silence_threshold,
            audio_dynamic_threshold=self.audio_dynamic_threshold,
            audio_noise_multiplier=self.audio_noise_multiplier,
            audio_max_dynamic_threshold=self.audio_max_dynamic_threshold,
            audio_preroll_seconds=self.audio_preroll_seconds,
            audio_normalize_enabled=self.audio_normalize_enabled,
            audio_dc_offset_filter=self.audio_dc_offset_filter,
            audio_target_peak=self.audio_target_peak,
            audio_max_gain=self.audio_max_gain,
        )


def float_pref(preferences: dict[str, Any], name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(preferences.get(name, default))
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, value))


def int_pref(preferences: dict[str, Any], name: str, default: int, minimum: int, maximum: int) -> int:
    try:
        value = int(preferences.get(name, default))
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, value))


def build_voice_runtime_config(preferences: dict[str, Any]) -> VoiceRuntimeConfig:
    hotword = str(preferences.get("hotword", "estagiario"))
    trigger_name = hotkey_name(preferences, "trigger_hotkey", "F8")
    trigger_vk = hotkey_vk(trigger_name, "F8")
    toggle_name = hotkey_name(preferences, "toggle_listening_hotkey", "F9")
    toggle_vk = hotkey_vk(toggle_name, "F9")

    conversation_prompt = str(
        preferences.get(
            "conversation_transcription_prompt",
            "Conversa casual em portugues do Brasil.",
        )
    ).strip()

    return VoiceRuntimeConfig(
        conversation_model_size=str(preferences.get("conversation_model_size", COMMAND_MODEL_SIZE)),
        default_min_speech_seconds=float_pref(preferences, "audio_min_speech_seconds", 0.25, 0.05, 2.0),
        default_max_silence_seconds=float_pref(preferences, "audio_max_silence_seconds", 0.75, 0.2, 3.0),
        silence_threshold=float_pref(preferences, "audio_silence_threshold", 0.01, 0.001, 0.2),
        audio_dynamic_threshold=bool(preferences.get("audio_dynamic_threshold", True)),
        audio_noise_multiplier=float_pref(preferences, "audio_noise_multiplier", 3.0, 1.2, 10.0),
        audio_max_dynamic_threshold=float_pref(preferences, "audio_max_dynamic_threshold", 0.04, 0.005, 0.3),
        audio_preroll_seconds=float_pref(preferences, "audio_preroll_seconds", 0.25, 0.0, 1.0),
        audio_normalize_enabled=bool(preferences.get("audio_normalize_enabled", True)),
        audio_dc_offset_filter=bool(preferences.get("audio_dc_offset_filter", True)),
        audio_target_peak=float_pref(preferences, "audio_target_peak", 0.75, 0.1, 0.98),
        audio_max_gain=float_pref(preferences, "audio_max_gain", 4.0, 1.0, 20.0),
        audio_diagnostic_seconds=float_pref(preferences, "audio_diagnostic_seconds", 4.0, 1.0, 15.0),
        whisper_command_vad_filter=bool(preferences.get("whisper_command_vad_filter", False)),
        whisper_conversation_vad_filter=bool(preferences.get("whisper_conversation_vad_filter", False)),
        whisper_hotword_vad_filter=bool(preferences.get("whisper_hotword_vad_filter", True)),
        whisper_command_beam_size=int_pref(preferences, "whisper_command_beam_size", 5, 1, 10),
        whisper_command_best_of=int_pref(preferences, "whisper_command_best_of", 5, 1, 10),
        whisper_conversation_beam_size=int_pref(preferences, "whisper_conversation_beam_size", 3, 1, 10),
        whisper_conversation_best_of=int_pref(preferences, "whisper_conversation_best_of", 3, 1, 10),
        whisper_hotword_beam_size=int_pref(preferences, "whisper_hotword_beam_size", 1, 1, 5),
        whisper_hotword_best_of=int_pref(preferences, "whisper_hotword_best_of", 1, 1, 5),
        hotword=hotword,
        hotword_listening_enabled=bool(preferences.get("hotword_listening_enabled", False)),
        hotword_timeout_seconds=float_pref(preferences, "hotword_timeout_seconds", 3.0, 0.8, 8.0),
        hotword_max_silence_seconds=float_pref(preferences, "hotword_max_silence_seconds", 0.5, 0.15, 2.0),
        hotword_min_speech_seconds=float_pref(preferences, "hotword_min_speech_seconds", 0.12, 0.05, 1.0),
        conversation_timeout_seconds=float_pref(preferences, "conversation_timeout_seconds", 7.0, 1.0, 12.0),
        conversation_max_silence_seconds=float_pref(preferences, "conversation_max_silence_seconds", 1.0, 0.25, 3.0),
        conversation_min_speech_seconds=float_pref(preferences, "conversation_min_speech_seconds", 0.35, 0.08, 2.0),
        conversation_prompt=conversation_prompt,
        hotword_prompt=f"Palavra de ativacao: {hotword}.",
        hotkey_name=trigger_name,
        hotkey_vk=trigger_vk,
        toggle_listening_hotkey_name=toggle_name,
        toggle_listening_hotkey_vk=toggle_vk,
        speech_interrupt_keys=speech_interrupt_keys(trigger_vk, toggle_vk),
    )
