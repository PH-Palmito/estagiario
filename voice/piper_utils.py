from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PiperTtsSettings:
    piper_exe: str
    model_path: str
    config_path: str
    speaker_id: str
    length_scale: str
    noise_scale: str
    noise_w: str


@dataclass(frozen=True)
class PiperTtsValidation:
    model: Path | None
    error: str | None


@dataclass(frozen=True)
class PiperWorkerRuntimeSettings:
    enabled: bool
    fallback_to_cli: bool
    timeout_seconds: float
    idle_seconds: float


@dataclass(frozen=True)
class PiperWorkerReadResult:
    error: str | None
    audio_bytes: bytes
    worker_warm: bool


@dataclass(frozen=True)
class PiperSynthesisPlan:
    text: str
    cache_enabled: bool
    cache_settings: list[str]
    chunks: tuple[str, ...]
    should_chunk: bool


def _float_setting(preferences: dict, name: str, default: float) -> str:
    try:
        return str(float(preferences.get(name, default)))
    except (TypeError, ValueError):
        return str(default)


def piper_tts_settings(preferences: dict) -> PiperTtsSettings:
    return PiperTtsSettings(
        piper_exe=str(preferences.get("piper_exe_path", "piper")).strip() or "piper",
        model_path=str(preferences.get("piper_model_path", "")).strip(),
        config_path=str(preferences.get("piper_config_path", "")).strip(),
        speaker_id=str(preferences.get("piper_speaker_id", "")).strip(),
        length_scale=_float_setting(preferences, "piper_length_scale", 1.0),
        noise_scale=_float_setting(preferences, "piper_noise_scale", 0.667),
        noise_w=_float_setting(preferences, "piper_noise_w", 0.8),
    )


def validate_piper_tts_settings(settings: PiperTtsSettings) -> PiperTtsValidation:
    if not settings.model_path:
        return PiperTtsValidation(model=None, error="Modelo do Piper nao configurado.")

    model = Path(settings.model_path)
    if not model.exists():
        return PiperTtsValidation(model=None, error=f"Modelo do Piper nao encontrado: {settings.model_path}")

    if settings.config_path and not Path(settings.config_path).exists():
        return PiperTtsValidation(model=None, error=f"Config do Piper nao encontrado: {settings.config_path}")

    return PiperTtsValidation(model=model, error=None)


def _float_pref(preferences: dict, name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(preferences.get(name, default))
    except (TypeError, ValueError):
        return default

    return max(minimum, min(maximum, value))


def piper_worker_runtime_settings(preferences: dict) -> PiperWorkerRuntimeSettings:
    return PiperWorkerRuntimeSettings(
        enabled=bool(preferences.get("piper_persistent_worker_enabled", True)),
        fallback_to_cli=bool(preferences.get("piper_worker_fallback_to_cli", True)),
        timeout_seconds=_float_pref(preferences, "piper_worker_timeout_seconds", 20.0, 3.0, 60.0),
        idle_seconds=_float_pref(preferences, "piper_worker_idle_seconds", 0.12, 0.03, 1.0),
    )


def piper_effective_worker_idle(idle_seconds: float, worker_warm: bool) -> float:
    return max(idle_seconds, 0.35 if not worker_warm else idle_seconds)


def piper_worker_read_size(available_bytes: int, max_bytes: int = 65536) -> int:
    if available_bytes <= 0:
        return 0
    return min(available_bytes, max_bytes)


def piper_worker_should_stop_reading(
    now: float,
    started: float,
    timeout_seconds: float,
    last_data_at: float | None,
    effective_idle_seconds: float,
) -> bool:
    if now - started > timeout_seconds:
        return True
    return last_data_at is not None and (now - last_data_at) >= effective_idle_seconds


def append_piper_audio_chunk(chunks: list[bytes], data: bytes, now: float) -> float | None:
    if not data:
        return None
    chunks.append(data)
    return now


def read_piper_worker_audio_loop(
    process,
    timeout_seconds: float,
    idle_seconds: float,
    worker_warm: bool,
    interrupt_pressed,
    stop_worker,
    read_stdout_chunk,
    monotonic,
    sleep,
) -> PiperWorkerReadResult:
    chunks: list[bytes] = []
    started = monotonic()
    last_data_at = None
    effective_idle = piper_effective_worker_idle(idle_seconds, worker_warm)

    stdout = process.stdout
    if stdout is None:
        return PiperWorkerReadResult(error="Worker Piper sem stdout.", audio_bytes=b"", worker_warm=worker_warm)

    while True:
        if interrupt_pressed():
            stop_worker()
            return PiperWorkerReadResult(error="Fala interrompida.", audio_bytes=b"", worker_warm=worker_warm)

        if process.poll() is not None:
            break

        now = monotonic()
        if piper_worker_should_stop_reading(now, started, timeout_seconds, last_data_at, effective_idle):
            break

        data = read_stdout_chunk(stdout)
        if data is None:
            break

        updated_at = append_piper_audio_chunk(chunks, data, monotonic())
        if updated_at is not None:
            last_data_at = updated_at
            continue

        sleep(0.01)

    return PiperWorkerReadResult(error=None, audio_bytes=b"".join(chunks), worker_warm=bool(chunks) or worker_warm)


def _extend_piper_optional_args(command: list[str], settings: PiperTtsSettings) -> list[str]:
    if settings.config_path:
        command.extend(["--config", settings.config_path])

    if settings.speaker_id:
        command.extend(["--speaker", settings.speaker_id])

    return command


def piper_cli_command(settings: PiperTtsSettings, model_path: str, output_path: str) -> list[str]:
    command = [
        settings.piper_exe,
        "--model",
        model_path,
        "--output_file",
        output_path,
        "--length_scale",
        settings.length_scale,
        "--noise_scale",
        settings.noise_scale,
        "--noise_w",
        settings.noise_w,
    ]
    return _extend_piper_optional_args(command, settings)


def piper_worker_command(settings: PiperTtsSettings, model_path: str) -> list[str]:
    command = [
        settings.piper_exe,
        "--model",
        model_path,
        "--output_raw",
        "--json-input",
        "--quiet",
        "--length_scale",
        settings.length_scale,
        "--noise_scale",
        settings.noise_scale,
        "--noise_w",
        settings.noise_w,
    ]
    return _extend_piper_optional_args(command, settings)


def piper_worker_payload(text: str) -> bytes:
    return json.dumps({"text": text}, ensure_ascii=False).encode("utf-8") + b"\n"


def write_piper_worker_payload(process, payload: bytes) -> None:
    if process.poll() is not None:
        raise RuntimeError("Worker Piper morreu antes da escrita.")
    if process.stdin is None:
        raise RuntimeError("Worker Piper sem stdin.")

    process.stdin.write(payload)
    process.stdin.flush()


def load_piper_sample_rate(config_path: str, default: int = 22050) -> int:
    try:
        data = json.loads(Path(config_path).read_text(encoding="utf-8"))
        audio = data.get("audio", {}) if isinstance(data, dict) else {}
        sample_rate = int(audio.get("sample_rate", default))
        if sample_rate > 0:
            return sample_rate
    except Exception:
        pass

    return default


def piper_worker_signature(
    piper_exe: str,
    model_path: str,
    config_path: str,
    speaker_id: str,
    length_scale: str,
    noise_scale: str,
    noise_w: str,
) -> tuple[str, ...]:
    return (
        piper_exe,
        model_path,
        config_path,
        speaker_id,
        length_scale,
        noise_scale,
        noise_w,
    )


def piper_cache_settings(
    model_path: str,
    config_path: str,
    speaker_id: str,
    length_scale: str,
    noise_scale: str,
    noise_w: str,
    preferences: dict,
) -> list[str]:
    effect = str(preferences.get("assistant_voice_effect", "")).strip().lower()
    effect_strength = str(preferences.get("assistant_voice_effect_strength", 0.0))
    return [
        model_path,
        config_path,
        speaker_id,
        length_scale,
        noise_scale,
        noise_w,
        effect,
        effect_strength,
    ]


def piper_synthesis_plan(
    text_for_tts: str,
    cache_settings: list[str],
    preferences: dict,
    chunk_threshold: int = 140,
) -> PiperSynthesisPlan:
    chunks = tuple(split_tts_text_for_piper(text_for_tts))
    return PiperSynthesisPlan(
        text=text_for_tts,
        cache_enabled=bool(preferences.get("tts_cache_enabled", True)),
        cache_settings=cache_settings,
        chunks=chunks,
        should_chunk=len(chunks) > 1 and len(text_for_tts) >= chunk_threshold,
    )


def split_tts_text_for_piper(text: str, max_chars: int = 170) -> list[str]:
    parts = []
    raw_segments = [segment.strip() for segment in re.split(r"\n+", text) if segment.strip()]

    for segment in raw_segments:
        if len(segment) <= max_chars:
            parts.append(segment)
            continue

        comma_segments = [piece.strip() for piece in re.split(r"(?<=,)\s+", segment) if piece.strip()]
        current = ""

        for piece in comma_segments:
            candidate = piece if not current else f"{current} {piece}"
            if len(candidate) <= max_chars:
                current = candidate
                continue

            if current:
                parts.append(current)
                current = ""

            if len(piece) <= max_chars:
                current = piece
                continue

            words = piece.split()
            buffer = ""
            for word in words:
                candidate = word if not buffer else f"{buffer} {word}"
                if len(candidate) <= max_chars:
                    buffer = candidate
                else:
                    if buffer:
                        parts.append(buffer)
                    buffer = word
            if buffer:
                current = buffer

        if current:
            parts.append(current)

    normalized_parts = [part.strip() for part in parts if part.strip()]
    merged_parts = []
    pending_prefix = ""

    for part in normalized_parts:
        compact = part.strip()
        is_tiny = len(compact) <= 6 or bool(re.fullmatch(r"\d+[.]?", compact))
        if is_tiny:
            pending_prefix = f"{pending_prefix} {compact}".strip()
            continue

        if pending_prefix:
            compact = f"{pending_prefix} {compact}".strip()
            pending_prefix = ""

        if merged_parts and re.search(r"\d+\.$", merged_parts[-1]) and re.match(r"^\d", compact):
            merged_parts[-1] = f"{merged_parts[-1][:-1]},{compact}".strip()
            continue

        merged_parts.append(compact)

    if pending_prefix:
        if merged_parts:
            merged_parts[-1] = f"{merged_parts[-1]} {pending_prefix}".strip()
        else:
            merged_parts.append(pending_prefix)

    return merged_parts
