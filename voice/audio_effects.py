from __future__ import annotations

from pathlib import Path

import numpy as np
from scipy.io.wavfile import read as read_wav
from scipy.io.wavfile import write as write_wav


def voice_effect_strength(preferences: dict, default: float = 0.35) -> float:
    try:
        value = float(preferences.get("assistant_voice_effect_strength", default))
    except (TypeError, ValueError):
        return default

    return max(0.0, min(1.0, value))


def apply_jarvis_audio_effect(path: str | Path, preferences: dict):
    effect = str(preferences.get("assistant_voice_effect", "")).strip().lower()
    if effect not in {"jarvis", "subtle_jarvis"}:
        return

    strength = voice_effect_strength(preferences)
    if strength <= 0:
        return

    try:
        sample_rate, data = read_wav(path)
    except Exception:
        return

    if data.size == 0:
        return

    original_dtype = data.dtype
    audio = data.astype(np.float32)

    if np.issubdtype(original_dtype, np.integer):
        max_value = float(np.iinfo(original_dtype).max)
        audio = audio / max_value

    if audio.ndim == 1:
        audio_2d = audio[:, None]
    else:
        audio_2d = audio

    processed = audio_2d.copy()

    emphasized = processed.copy()
    emphasized[1:] = processed[1:] - (0.16 * strength * processed[:-1])
    processed = ((1.0 - (0.22 * strength)) * processed) + ((0.22 * strength) * emphasized)

    for delay_ms, gain in ((14, 0.055), (31, 0.035)):
        delay = max(1, int(sample_rate * delay_ms / 1000))
        delayed = np.zeros_like(processed)
        delayed[delay:] = processed[:-delay]
        processed += delayed * gain * strength

    drive = 1.0 + (1.2 * strength)
    processed = np.tanh(processed * drive) / np.tanh(drive)

    peak = float(np.max(np.abs(processed))) if processed.size else 0.0
    if peak > 0:
        processed = processed * min(0.92 / peak, 1.0)

    if audio.ndim == 1:
        processed = processed[:, 0]

    output = np.clip(processed, -1.0, 1.0)
    output = (output * 32767.0).astype(np.int16)

    try:
        write_wav(path, sample_rate, output)
    except Exception:
        pass
