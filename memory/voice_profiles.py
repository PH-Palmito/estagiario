from pathlib import Path

from memory.json_store import read_json_file, update_json_file, write_json_atomic

VOICE_PREFERENCES_PATH = Path(__file__).resolve().parent / "voice_preferences.json"

VOICE_PROFILES = {
    "faber-rapido": {
        "piper_length_scale": 0.88,
        "piper_noise_scale": 0.52,
        "piper_noise_w": 0.62,
        "assistant_style": "elegante",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "off",
        "assistant_voice_effect_strength": 0.0,
        "startup_voice_greeting": "Modo voz ativado. Pronto.",
    },
    "faber-claro": {
        "piper_length_scale": 0.96,
        "piper_noise_scale": 0.46,
        "piper_noise_w": 0.58,
        "assistant_style": "elegante",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "off",
        "assistant_voice_effect_strength": 0.0,
        "startup_voice_greeting": "Modo voz ativado. Pronto para começar.",
    },
    "faber-calmo": {
        "piper_length_scale": 1.08,
        "piper_noise_scale": 0.5,
        "piper_noise_w": 0.64,
        "assistant_style": "elegante",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "off",
        "assistant_voice_effect_strength": 0.0,
        "startup_voice_greeting": "Modo voz ativado. Estou pronto para começar.",
    },
    "faber-jarvis": {
        "piper_length_scale": 1.03,
        "piper_noise_scale": 0.4,
        "piper_noise_w": 0.52,
        "assistant_style": "elegante",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "subtle_jarvis",
        "assistant_voice_effect_strength": 0.06,
        "startup_voice_greeting": "Sistemas online. Pronto para começar.",
    },
    "assistente": {
        "piper_length_scale": 1.06,
        "piper_noise_scale": 0.54,
        "piper_noise_w": 0.66,
        "assistant_style": "assistente",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "off",
        "assistant_voice_effect_strength": 0.0,
        "startup_voice_greeting": "Sistemas prontos. Estou ouvindo quando precisar.",
    },
    "assistente-cinema": {
        "piper_length_scale": 1.14,
        "piper_noise_scale": 0.42,
        "piper_noise_w": 0.56,
        "assistant_style": "assistente",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "subtle_jarvis",
        "assistant_voice_effect_strength": 0.1,
        "startup_voice_greeting": "Sistemas prontos. Interface ativa. Aguardando suas instrucoes.",
    },
    "jarvis": {
        "piper_length_scale": 0.95,
        "piper_noise_scale": 0.38,
        "piper_noise_w": 0.58,
        "assistant_style": "jarvis",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "off",
        "assistant_voice_effect_strength": 0.0,
        "startup_voice_greeting": "Sistemas online. À sua disposição.",
    },
    "jarvis-calmo": {
        "piper_length_scale": 1.02,
        "piper_noise_scale": 0.34,
        "piper_noise_w": 0.52,
        "assistant_style": "jarvis",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "off",
        "assistant_voice_effect_strength": 0.0,
        "startup_voice_greeting": "Sistemas online. Aguardando suas instruções.",
    },
    "jarvis-firme": {
        "piper_length_scale": 0.9,
        "piper_noise_scale": 0.32,
        "piper_noise_w": 0.48,
        "assistant_style": "jarvis",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "off",
        "assistant_voice_effect_strength": 0.0,
        "startup_voice_greeting": "Pronto, senhor. Sistemas operacionais.",
    },
    "jarvis-console": {
        "piper_length_scale": 1.12,
        "piper_noise_scale": 0.32,
        "piper_noise_w": 0.48,
        "assistant_style": "jarvis",
        "assistant_brief_confirmations": True,
        "assistant_voice_effect": "subtle_jarvis",
        "assistant_voice_effect_strength": 0.18,
        "startup_voice_greeting": "Sistemas online. Interface de voz pronta. Aguardando instruções.",
    },
    "natural": {
        "piper_length_scale": 1.0,
        "piper_noise_scale": 0.667,
        "piper_noise_w": 0.8,
        "assistant_style": "natural",
        "assistant_brief_confirmations": False,
        "assistant_voice_effect": "off",
        "assistant_voice_effect_strength": 0.0,
        "startup_voice_greeting": "Modo voz ativado. Pronto para começar.",
    },
}


def load_preferences():
    return read_json_file(VOICE_PREFERENCES_PATH, {}, validator=lambda value: isinstance(value, dict))


def save_preferences(preferences):
    write_json_atomic(VOICE_PREFERENCES_PATH, preferences, indent=2, trailing_newline=True)


def apply_voice_profile(name: str):
    profile_name = name.strip().lower()
    if profile_name not in VOICE_PROFILES:
        return False, f"Perfil de voz desconhecido: {name}."

    update_json_file(
        VOICE_PREFERENCES_PATH,
        {},
        lambda preferences: {**dict(preferences or {}), **VOICE_PROFILES[profile_name]},
        validator=lambda value: isinstance(value, dict),
        indent=2,
        trailing_newline=True,
    )
    return True, f"Perfil de voz aplicado: {profile_name}."


def list_voice_profiles():
    return sorted(VOICE_PROFILES)
