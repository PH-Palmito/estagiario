import json
from pathlib import Path

from memory.supabase_sync import sync_memory_state_safely


FILE = Path("memory/voice_preferences.json")

DEFAULTS = {
    "hotword": "estagiario",
    "hotword_listening_enabled": False,
    "trigger_hotkey": "F8",
    "toggle_listening_hotkey": "F9",
    "activation_sound": True,
    "activation_sound_hz": 880,
    "activation_sound_ms": 120,
    "tts_enabled": True,
    "tts_engine": "windows",
    "tts_rate": 0,
    "tts_volume": 100,
    "tts_voice_name": "",
    "tts_voice_culture": "pt-BR",
    "tts_cache_enabled": True,
    "tts_wait_for_playback": False,
    "tts_warm_cache_on_startup": True,
    "tts_pronunciations_enabled": True,
    "gemini_tts_voice_name": "Kore",
    "gemini_tts_language_code": "pt-BR",
    "gemini_tts_timeout_seconds": 60,
    "gemini_tts_fallback_to_piper": True,
    "piper_exe_path": "piper",
    "piper_model_path": "",
    "piper_config_path": "",
    "piper_speaker_id": "",
    "piper_length_scale": 1.0,
    "piper_noise_scale": 0.667,
    "piper_noise_w": 0.8,
    "piper_fallback_to_windows": True,
    "piper_persistent_worker_enabled": True,
    "piper_worker_timeout_seconds": 20.0,
    "piper_worker_idle_seconds": 0.35,
    "piper_worker_fallback_to_cli": True,
    "assistant_humor_enabled": True,
    "assistant_humor_level": 2,
    "assistant_humor_style": "jarvis",
    "assistant_style": "jarvis",
    "assistant_address_user": "senhor",
    "assistant_brief_confirmations": True,
    "chat_enabled": True,
    "chat_model": "qwen2.5:0.5b",
    "chat_timeout_seconds": 8,
    "audio_silence_threshold": 0.01,
    "audio_dynamic_threshold": True,
    "audio_noise_multiplier": 3.0,
    "audio_max_dynamic_threshold": 0.04,
    "audio_min_speech_seconds": 0.25,
    "audio_max_silence_seconds": 0.75,
    "audio_preroll_seconds": 0.25,
    "audio_normalize_enabled": True,
    "audio_dc_offset_filter": True,
    "audio_target_peak": 0.75,
    "audio_max_gain": 4.0,
    "audio_diagnostic_seconds": 4.0,
    "audio_input_device": "",
    "whisper_command_vad_filter": False,
    "whisper_hotword_vad_filter": True,
    "whisper_command_beam_size": 5,
    "whisper_command_best_of": 5,
    "whisper_hotword_beam_size": 1,
    "whisper_hotword_best_of": 1,
    "hotword_timeout_seconds": 3.0,
    "hotword_min_speech_seconds": 0.12,
    "hotword_max_silence_seconds": 0.5,
}


def load_voice_preferences():
    if not FILE.exists():
        return dict(DEFAULTS)

    try:
        data = json.loads(FILE.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return dict(DEFAULTS)
    except Exception:
        return dict(DEFAULTS)

    merged = dict(DEFAULTS)
    merged.update(data)
    return merged


def save_voice_preferences(preferences: dict):
    FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(preferences or {})
    FILE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    sync_memory_state_safely("voice_preferences", payload, category="preferences")


def update_voice_preferences(changes: dict):
    preferences = load_voice_preferences()
    preferences.update(changes)
    save_voice_preferences(preferences)
    return preferences
