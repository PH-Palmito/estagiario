from __future__ import annotations

import hashlib
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy.io.wavfile import write as write_wav_file


def save_wav(path: str | Path, audio: np.ndarray, sample_rate: int):
    clipped = np.clip(audio, -1.0, 1.0)
    pcm = (clipped * 32767).astype(np.int16)
    write_wav_file(str(path), sample_rate, pcm)


def save_temp_wav(audio: np.ndarray, sample_rate: int) -> str:
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    temp.close()
    save_wav(temp.name, audio, sample_rate)
    return temp.name


def wav_duration_seconds(path: str | Path, default: float = 10.0) -> float:
    try:
        with wave.open(str(path), "rb") as wav_file:
            frame_count = wav_file.getnframes()
            frame_rate = wav_file.getframerate()
            if frame_rate > 0:
                return frame_count / float(frame_rate)
    except Exception:
        pass

    return default


def tts_cache_path(engine: str, text: str, settings: list[str], cache_root: str | Path = Path(".tmp") / "tts_cache") -> Path:
    root = Path(cache_root)
    root.mkdir(parents=True, exist_ok=True)
    digest_source = "\n".join([engine, text, *settings])
    digest = hashlib.sha256(digest_source.encode("utf-8", errors="replace")).hexdigest()
    return root / f"{digest}.wav"


def write_raw_pcm_to_wav(output_path: str | Path, audio_bytes: bytes, sample_rate: int):
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_bytes)
