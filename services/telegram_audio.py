from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any, Callable

import requests

from services.telegram_polling import telegram_api_url


TELEGRAM_FILE_API = "https://api.telegram.org/file/bot{token}/{file_path}"
TELEGRAM_AUDIO_DIR = Path("memory/telegram_audio")
_WHISPER_MODELS: dict[str, object] = {}


def _safe_file_stem(file_id: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(file_id or "").strip())
    return stem[:80] or "telegram-audio"


def _extension_from_file_path(file_path: str) -> str:
    suffix = Path(str(file_path or "")).suffix.strip()
    return suffix if suffix else ".oga"


def telegram_download_url(token: str, file_path: str) -> str:
    return TELEGRAM_FILE_API.format(token=str(token or "").strip(), file_path=str(file_path or "").lstrip("/"))


def get_telegram_file_path(
    token: str,
    file_id: str,
    *,
    requests_get: Callable[..., object] = requests.get,
    timeout_seconds: int = 30,
) -> str:
    response = requests_get(
        telegram_api_url(token, "getFile"),
        params={"file_id": file_id},
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    payload = response.json()
    result = payload.get("result") if isinstance(payload, dict) else {}
    file_path = str((result or {}).get("file_path") or "").strip()
    if not file_path:
        raise RuntimeError("Telegram nao retornou file_path para o audio.")
    return file_path


def download_telegram_audio(
    token: str,
    file_id: str,
    *,
    output_dir: Path | None = None,
    requests_get: Callable[..., object] = requests.get,
    timeout_seconds: int = 30,
) -> Path:
    if not token:
        raise RuntimeError("Token do Telegram nao configurado.")
    if not file_id:
        raise RuntimeError("file_id do audio nao informado.")

    file_path = get_telegram_file_path(
        token,
        file_id,
        requests_get=requests_get,
        timeout_seconds=timeout_seconds,
    )
    response = requests_get(
        telegram_download_url(token, file_path),
        timeout=timeout_seconds,
    )
    response.raise_for_status()
    target_dir = output_dir or TELEGRAM_AUDIO_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{_safe_file_stem(file_id)}{_extension_from_file_path(file_path)}"
    target.write_bytes(getattr(response, "content", b"") or b"")
    return target


def _get_whisper_model(model_size: str):
    key = str(model_size or "small").strip() or "small"
    if key not in _WHISPER_MODELS:
        from faster_whisper import WhisperModel

        compute_type = os.getenv("AXEL_TELEGRAM_WHISPER_COMPUTE_TYPE", "int8")
        _WHISPER_MODELS[key] = WhisperModel(key, device="cpu", compute_type=compute_type)
    return _WHISPER_MODELS[key]


def transcribe_audio_file(
    path: Path,
    *,
    model_size: str | None = None,
    get_model: Callable[[str], Any] = _get_whisper_model,
) -> str:
    model_name = str(model_size or os.getenv("AXEL_TELEGRAM_WHISPER_MODEL", "small")).strip() or "small"
    model = get_model(model_name)
    segments, _info = model.transcribe(
        str(path),
        language="pt",
        task="transcribe",
        vad_filter=True,
        beam_size=5,
        best_of=5,
        temperature=0.0,
        condition_on_previous_text=False,
    )
    return " ".join(segment.text.strip() for segment in segments).strip()


def transcribe_telegram_audio_request(
    request,
    *,
    token: str,
    download_audio: Callable[..., Path] = download_telegram_audio,
    transcribe_file: Callable[[Path], str] = transcribe_audio_file,
) -> str:
    path = download_audio(token, request.media_file_id)
    return transcribe_file(path)


def make_telegram_audio_transcriber(token: str):
    def _transcribe(request) -> str:
        return transcribe_telegram_audio_request(request, token=token)

    return _transcribe
