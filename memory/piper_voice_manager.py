import json
import shutil
from pathlib import Path

from huggingface_hub import hf_hub_download


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_PREFERENCES_PATH = PROJECT_ROOT / "memory" / "voice_preferences.json"
PIPER_MODELS_DIR = PROJECT_ROOT / "models" / "piper"
PIPER_REPO_ID = "rhasspy/piper-voices"

AVAILABLE_PIPER_VOICES = {
    "pt_BR-cadu-medium": {
        "label": "Cadu pt-BR medium",
        "remote_dir": "pt/pt_BR/cadu/medium",
        "model": "pt_BR-cadu-medium.onnx",
        "config": "pt_BR-cadu-medium.onnx.json",
    },
    "pt_BR-faber-medium": {
        "label": "Faber pt-BR medium",
        "remote_dir": "pt/pt_BR/faber/medium",
        "model": "pt_BR-faber-medium.onnx",
        "config": "pt_BR-faber-medium.onnx.json",
    },
    "pt_BR-jeff-medium": {
        "label": "Jeff pt-BR medium",
        "remote_dir": "pt/pt_BR/jeff/medium",
        "model": "pt_BR-jeff-medium.onnx",
        "config": "pt_BR-jeff-medium.onnx.json",
    },
    "pt_BR-edresson-low": {
        "label": "Edresson pt-BR low",
        "remote_dir": "pt/pt_BR/edresson/low",
        "model": "pt_BR-edresson-low.onnx",
        "config": "pt_BR-edresson-low.onnx.json",
    },
}


def load_preferences():
    try:
        return json.loads(VOICE_PREFERENCES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def save_preferences(preferences):
    VOICE_PREFERENCES_PATH.write_text(
        json.dumps(preferences, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def piper_voice_dir(key: str) -> Path:
    return PIPER_MODELS_DIR / key


def piper_voice_paths(key: str):
    voice = AVAILABLE_PIPER_VOICES.get(key)
    if not voice:
        return None, None

    voice_dir = piper_voice_dir(key)
    return voice_dir / voice["model"], voice_dir / voice["config"]


def is_voice_installed(key: str) -> bool:
    model_path, config_path = piper_voice_paths(key)
    return bool(model_path and config_path and model_path.exists() and config_path.exists())


def list_piper_voices():
    rows = []
    for key, voice in AVAILABLE_PIPER_VOICES.items():
        rows.append(
            {
                "key": key,
                "label": voice["label"],
                "installed": is_voice_installed(key),
            }
        )
    return rows


def download_piper_voice(key: str):
    voice = AVAILABLE_PIPER_VOICES.get(key)
    if not voice:
        return False, f"Voz Piper desconhecida: {key}."

    voice_dir = piper_voice_dir(key)
    voice_dir.mkdir(parents=True, exist_ok=True)

    try:
        for filename in (voice["model"], voice["config"]):
            remote_file = f"{voice['remote_dir']}/{filename}"
            downloaded = hf_hub_download(
                repo_id=PIPER_REPO_ID,
                filename=remote_file,
                repo_type="model",
            )
            shutil.copy2(downloaded, voice_dir / filename)
    except Exception as exc:
        return False, f"Nao consegui baixar {key}: {exc}"

    return True, f"Voz instalada: {key}."


def apply_piper_voice(key: str):
    if key not in AVAILABLE_PIPER_VOICES:
        return False, f"Voz Piper desconhecida: {key}."

    if not is_voice_installed(key):
        return False, f"Voz Piper ainda nao instalada: {key}."

    model_path, config_path = piper_voice_paths(key)
    preferences = load_preferences()
    preferences["tts_engine"] = "piper"
    preferences["piper_model_path"] = str(model_path)
    preferences["piper_config_path"] = str(config_path)
    preferences["piper_speaker_id"] = ""
    preferences["assistant_style"] = "natural"
    preferences["assistant_brief_confirmations"] = False
    preferences["assistant_voice_effect"] = "off"
    preferences["assistant_voice_effect_strength"] = 0.0
    save_preferences(preferences)
    return True, f"Voz Piper aplicada: {key}."
