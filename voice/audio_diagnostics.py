from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import numpy as np


def format_audio_stats(*, label: str, audio: np.ndarray, sample_rate: int, chunk_levels: Callable[[np.ndarray], tuple[float, float]]) -> str:
    peak, rms = chunk_levels(audio)
    duration = audio.size / sample_rate if audio.size else 0.0
    return f"{label}: duracao={duration:.2f}s pico={peak:.4f} rms={rms:.4f}"


def run_audio_diagnostic(
    *,
    seconds: float | None,
    default_seconds: float,
    sample_rate: int,
    command_model_size: str,
    command_prompt: str,
    whisper_command_beam_size: int,
    whisper_command_best_of: int,
    whisper_command_vad_filter: bool,
    active_input_device_info: Callable[[], dict | None],
    record_fixed_audio: Callable[[float], np.ndarray],
    preprocess_audio: Callable[[np.ndarray], np.ndarray],
    save_wav: Callable[[str | Path, np.ndarray], None],
    transcribe_audio: Callable[..., object],
    chunk_levels: Callable[[np.ndarray], tuple[float, float]],
) -> str:
    duration = seconds if seconds is not None else default_seconds
    duration = max(1.0, min(15.0, float(duration)))
    active_device = active_input_device_info()

    try:
        raw_audio = record_fixed_audio(duration)
    except Exception as exc:
        return f"Falha ao gravar diagnostico de audio: {exc}"

    processed_audio = preprocess_audio(raw_audio)
    output_dir = Path("memory") / "audio_diagnostics"
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    raw_path = output_dir / f"audio_raw_{stamp}.wav"
    processed_path = output_dir / f"audio_processed_{stamp}.wav"

    save_wav(raw_path, raw_audio)
    save_wav(processed_path, processed_audio)
    raw_transcription = transcribe_audio(
        raw_audio,
        model_size=command_model_size,
        prompt=command_prompt,
        beam_size=whisper_command_beam_size,
        best_of=whisper_command_best_of,
        vad_filter=whisper_command_vad_filter,
        preprocess=False,
    )
    processed_transcription = transcribe_audio(
        processed_audio,
        model_size=command_model_size,
        prompt=command_prompt,
        beam_size=whisper_command_beam_size,
        best_of=whisper_command_best_of,
        vad_filter=whisper_command_vad_filter,
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
                else "Microfone usado: padrao do Windows"
            ),
            format_audio_stats(label="Bruto", audio=raw_audio, sample_rate=sample_rate, chunk_levels=chunk_levels),
            format_audio_stats(
                label="Processado",
                audio=processed_audio,
                sample_rate=sample_rate,
                chunk_levels=chunk_levels,
            ),
            f"Whisper bruto: {raw_text}",
            f"Whisper processado: {processed_text}",
            f"Arquivo bruto: {raw_path.resolve()}",
            f"Arquivo processado: {processed_path.resolve()}",
        ]
    )
