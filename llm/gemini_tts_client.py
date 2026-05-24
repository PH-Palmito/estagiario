import base64
import wave
from pathlib import Path

import requests

from config import GEMINI_API_KEY, GEMINI_TTS_MODEL

GEMINI_TTS_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _post_tts(payload: dict, model: str, timeout_seconds: int):
    session = requests.Session()
    session.trust_env = False
    response = session.post(
        GEMINI_TTS_API_URL.format(model=model),
        headers={
            "x-goog-api-key": GEMINI_API_KEY,
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def synthesize_gemini_tts_pcm(
    text: str,
    *,
    voice_name: str = "Kore",
    language_code: str = "pt-BR",
    model: str = GEMINI_TTS_MODEL,
    timeout_seconds: int = 60,
) -> bytes:
    if not GEMINI_API_KEY:
        raise RuntimeError("Gemini API key nao configurada.")

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": str(text or "").strip(),
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseModalities": ["AUDIO"],
            "speechConfig": {
                "languageCode": language_code,
                "voiceConfig": {
                    "prebuiltVoiceConfig": {
                        "voiceName": voice_name,
                    }
                },
            },
        },
    }
    data = _post_tts(payload, model=model, timeout_seconds=timeout_seconds)
    candidates = data.get("candidates") or []
    if not candidates:
        raise RuntimeError("Gemini TTS retornou resposta vazia.")
    parts = ((candidates[0].get("content") or {}).get("parts")) or []
    inline_data = next((part.get("inlineData") or part.get("inline_data") or {} for part in parts if part.get("inlineData") or part.get("inline_data")), {})
    encoded = str(inline_data.get("data") or "").strip()
    if not encoded:
        raise RuntimeError("Gemini TTS nao retornou audio.")
    return base64.b64decode(encoded)


def save_pcm_as_wav(
    pcm_bytes: bytes,
    output_path: str | Path,
    *,
    channels: int = 1,
    rate: int = 24000,
    sample_width: int = 2,
) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(rate)
        wav_file.writeframes(pcm_bytes)
    return path


def synthesize_gemini_tts_to_wav(
    text: str,
    output_path: str | Path,
    *,
    voice_name: str = "Kore",
    language_code: str = "pt-BR",
    model: str = GEMINI_TTS_MODEL,
    timeout_seconds: int = 60,
) -> Path:
    pcm_bytes = synthesize_gemini_tts_pcm(
        text,
        voice_name=voice_name,
        language_code=language_code,
        model=model,
        timeout_seconds=timeout_seconds,
    )
    return save_pcm_as_wav(pcm_bytes, output_path)
