from __future__ import annotations

import ctypes
import msvcrt
import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

from voice.audio_effects import apply_jarvis_audio_effect
from voice.audio_files import write_raw_pcm_to_wav
from voice.piper_utils import (
    load_piper_sample_rate,
    piper_cli_command,
    piper_worker_command,
    piper_worker_payload,
    piper_worker_read_size,
    piper_worker_runtime_settings,
    piper_worker_signature,
    read_piper_worker_audio_loop,
    write_piper_worker_payload,
)

kernel32 = ctypes.windll.kernel32

_PIPER_WORKER_LOCK = Lock()
_PIPER_WORKER_PROCESS = None
_PIPER_WORKER_SIGNATURE = None
_PIPER_WORKER_SAMPLE_RATE = 22050
_PIPER_WORKER_WARM = False


@dataclass(frozen=True)
class PiperRuntimeResult:
    error: str = ""


def stop_piper_worker_locked() -> None:
    global _PIPER_WORKER_PROCESS, _PIPER_WORKER_SIGNATURE, _PIPER_WORKER_WARM

    process = _PIPER_WORKER_PROCESS
    _PIPER_WORKER_PROCESS = None
    _PIPER_WORKER_SIGNATURE = None
    _PIPER_WORKER_WARM = False

    if not process:
        return

    try:
        if process.stdin:
            try:
                process.stdin.close()
            except Exception:
                pass
        process.terminate()
        process.wait(timeout=1.5)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass


def ensure_piper_worker(settings, model_path: str, *, popen: Callable[..., Any] = subprocess.Popen):
    global _PIPER_WORKER_PROCESS, _PIPER_WORKER_SIGNATURE, _PIPER_WORKER_SAMPLE_RATE, _PIPER_WORKER_WARM

    signature = piper_worker_signature(
        settings.piper_exe,
        model_path,
        settings.config_path,
        settings.speaker_id,
        settings.length_scale,
        settings.noise_scale,
        settings.noise_w,
    )

    with _PIPER_WORKER_LOCK:
        process = _PIPER_WORKER_PROCESS
        if process is not None and process.poll() is None and signature == _PIPER_WORKER_SIGNATURE:
            return process

        stop_piper_worker_locked()

        process = popen(
            piper_worker_command(settings, model_path),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            bufsize=0,
        )

        _PIPER_WORKER_PROCESS = process
        _PIPER_WORKER_SIGNATURE = signature
        _PIPER_WORKER_SAMPLE_RATE = load_piper_sample_rate(settings.config_path)
        _PIPER_WORKER_WARM = False
        return process


def piper_stdout_available(stdout) -> int:
    try:
        handle = msvcrt.get_osfhandle(stdout.fileno())
        total_available = ctypes.c_ulong(0)
        ok = kernel32.PeekNamedPipe(
            ctypes.c_void_p(handle),
            None,
            0,
            None,
            ctypes.byref(total_available),
            None,
        )
        return int(total_available.value) if ok else 0
    except Exception:
        return 0


def read_piper_stdout_chunk(stdout) -> bytes | None:
    read_size = piper_worker_read_size(piper_stdout_available(stdout))
    if read_size <= 0:
        return b""

    try:
        return os.read(stdout.fileno(), read_size)
    except Exception:
        return None


def read_piper_worker_audio(process, timeout_seconds: float, idle_seconds: float, *, interrupt_pressed: Callable[[], bool]):
    global _PIPER_WORKER_WARM

    result = read_piper_worker_audio_loop(
        process,
        timeout_seconds=timeout_seconds,
        idle_seconds=idle_seconds,
        worker_warm=_PIPER_WORKER_WARM,
        interrupt_pressed=interrupt_pressed,
        stop_worker=stop_piper_worker_locked,
        read_stdout_chunk=read_piper_stdout_chunk,
        monotonic=time.monotonic,
        sleep=time.sleep,
    )
    _PIPER_WORKER_WARM = result.worker_warm
    if result.error:
        return PiperRuntimeResult(error=result.error), result.audio_bytes
    return None, result.audio_bytes


def run_piper_synthesis(
    text_for_tts: str,
    output_path: str,
    settings,
    model: Path,
    *,
    preferences: dict,
    interrupt_pressed: Callable[[], bool],
    run_process: Callable[..., Any] = subprocess.run,
    popen: Callable[..., Any] = subprocess.Popen,
) -> PiperRuntimeResult | None:
    worker_settings = piper_worker_runtime_settings(preferences)

    if worker_settings.enabled:
        try:
            process = ensure_piper_worker(settings, str(model), popen=popen)
            payload = piper_worker_payload(text_for_tts)

            with _PIPER_WORKER_LOCK:
                write_piper_worker_payload(process, payload)

            interrupt_result, audio_bytes = read_piper_worker_audio(
                process,
                timeout_seconds=worker_settings.timeout_seconds,
                idle_seconds=worker_settings.idle_seconds,
                interrupt_pressed=interrupt_pressed,
            )

            if interrupt_result:
                return interrupt_result

            if audio_bytes:
                write_raw_pcm_to_wav(output_path, audio_bytes, _PIPER_WORKER_SAMPLE_RATE)
                apply_jarvis_audio_effect(output_path, preferences)
                return None

            with _PIPER_WORKER_LOCK:
                stop_piper_worker_locked()

        except Exception as exc:
            with _PIPER_WORKER_LOCK:
                stop_piper_worker_locked()

            if not worker_settings.fallback_to_cli:
                return PiperRuntimeResult(error=f"Worker persistente do Piper falhou: {exc}")

        if not worker_settings.fallback_to_cli:
            return PiperRuntimeResult(error="Worker persistente do Piper falhou.")

    command = piper_cli_command(settings, str(model), output_path)

    try:
        completed = run_process(
            command,
            input=text_for_tts,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except FileNotFoundError:
        return PiperRuntimeResult(error=f"Piper nao encontrado: {settings.piper_exe}")
    except subprocess.TimeoutExpired:
        return PiperRuntimeResult(error="Tempo limite atingido ao falar com Piper.")
    except Exception as exc:
        return PiperRuntimeResult(error=f"Falha ao usar Piper: {exc}")

    if completed.returncode != 0:
        error = (completed.stderr or completed.stdout or "").strip()
        return PiperRuntimeResult(error=error or "Piper nao conseguiu gerar audio.")

    apply_jarvis_audio_effect(output_path, preferences)
    return None
