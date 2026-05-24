from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
import sounddevice as sd


@dataclass(frozen=True)
class AudioCaptureConfig:
    sample_rate: int
    frame_size: int
    default_max_record_seconds: float
    silence_threshold: float
    audio_dynamic_threshold: bool
    audio_noise_multiplier: float
    audio_max_dynamic_threshold: float
    audio_preroll_seconds: float
    audio_normalize_enabled: bool
    audio_dc_offset_filter: bool
    audio_target_peak: float
    audio_max_gain: float


def chunk_levels(chunk: np.ndarray) -> tuple[float, float]:
    if not chunk.size:
        return 0.0, 0.0

    peak = float(np.max(np.abs(chunk)))
    rms = float(np.sqrt(np.mean(np.square(chunk))))
    return peak, rms


def chunk_has_speech(chunk: np.ndarray, threshold: float) -> bool:
    peak, rms = chunk_levels(chunk)
    return peak >= threshold or rms >= threshold * 0.35


def preprocess_audio(audio: np.ndarray, config: AudioCaptureConfig) -> np.ndarray:
    if audio.size == 0:
        return audio

    processed = audio.astype(np.float32, copy=True)

    if config.audio_dc_offset_filter:
        processed -= float(np.mean(processed))

    peak, _rms = chunk_levels(processed)

    if config.audio_normalize_enabled and peak > 0.0001:
        gain = min(config.audio_max_gain, config.audio_target_peak / peak)
        processed *= gain

    return np.clip(processed, -1.0, 1.0)


def record_audio(
    timeout_seconds: float,
    min_speech_seconds: float,
    max_silence_seconds: float,
    config: AudioCaptureConfig,
    resolve_input_device: Callable[[], tuple[int | None, dict | None]],
) -> np.ndarray:
    input_device, _device_info = resolve_input_device()
    chunks = []
    preroll_chunks = deque(
        maxlen=max(1, int((config.sample_rate * config.audio_preroll_seconds) / config.frame_size))
    )
    speech_detected = False
    speech_frames = 0
    silence_after_speech_frames = 0
    noise_floor = 0.0
    effective_threshold = config.silence_threshold
    max_frames = int(config.sample_rate * min(float(timeout_seconds), config.default_max_record_seconds))

    with sd.InputStream(
        samplerate=config.sample_rate,
        channels=1,
        dtype="float32",
        device=input_device,
        blocksize=config.frame_size,
    ) as stream:
        collected_frames = 0

        while collected_frames < max_frames:
            chunk, _overflowed = stream.read(config.frame_size)
            chunk = chunk.reshape(-1)
            collected_frames += len(chunk)

            peak, _rms = chunk_levels(chunk)
            has_speech = chunk_has_speech(chunk, effective_threshold)

            if not speech_detected and not has_speech:
                preroll_chunks.append(chunk)

                if config.audio_dynamic_threshold:
                    noise_floor = (noise_floor * 0.85) + (peak * 0.15)
                    effective_threshold = min(
                        config.audio_max_dynamic_threshold,
                        max(config.silence_threshold, noise_floor * config.audio_noise_multiplier),
                    )
                continue

            if has_speech:
                if not speech_detected:
                    chunks.extend(preroll_chunks)
                    preroll_chunks.clear()
                speech_detected = True
                speech_frames += len(chunk)
                silence_after_speech_frames = 0
                chunks.append(chunk)
            elif speech_detected:
                silence_after_speech_frames += len(chunk)
                chunks.append(chunk)

            enough_speech = speech_frames >= int(config.sample_rate * min_speech_seconds)
            enough_silence = silence_after_speech_frames >= int(config.sample_rate * max_silence_seconds)

            if speech_detected and enough_speech and enough_silence:
                break

    if not chunks:
        if not preroll_chunks:
            return np.array([], dtype=np.float32)
        return np.concatenate(list(preroll_chunks))

    return np.concatenate(chunks)


def record_fixed_audio(
    duration_seconds: float,
    config: AudioCaptureConfig,
    resolve_input_device: Callable[[], tuple[int | None, dict | None]],
) -> np.ndarray:
    input_device, _device_info = resolve_input_device()
    chunks = []
    total_frames = int(config.sample_rate * duration_seconds)

    with sd.InputStream(
        samplerate=config.sample_rate,
        channels=1,
        dtype="float32",
        device=input_device,
        blocksize=config.frame_size,
    ) as stream:
        collected_frames = 0
        while collected_frames < total_frames:
            chunk, _overflowed = stream.read(min(config.frame_size, total_frames - collected_frames))
            chunk = chunk.reshape(-1)
            chunks.append(chunk)
            collected_frames += len(chunk)

    if not chunks:
        return np.array([], dtype=np.float32)

    return np.concatenate(chunks)


def audio_has_signal(audio: np.ndarray, config: AudioCaptureConfig) -> bool:
    if audio.size == 0:
        return False

    return chunk_has_speech(audio, config.silence_threshold)
