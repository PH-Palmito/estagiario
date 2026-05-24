from __future__ import annotations

import time
import winsound
from collections.abc import Callable
from pathlib import Path


def stop_playback():
    winsound.PlaySound(None, 0)


def play_wav_async(path: str | Path):
    winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)


def wait_for_wav_playback(
    path: str | Path,
    duration_seconds: Callable[[str | Path], float],
    interrupt_pressed: Callable[[], bool],
    *,
    now: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> bool:
    duration = duration_seconds(path)
    started_at = now()
    while now() - started_at < duration + 0.15:
        if interrupt_pressed():
            stop_playback()
            return True
        sleep(0.03)

    return False


def play_wav(
    path: str | Path,
    duration_seconds: Callable[[str | Path], float],
    interrupt_pressed: Callable[[], bool],
    wait_for_playback: bool,
) -> bool:
    play_wav_async(path)
    if not wait_for_playback:
        return False

    return wait_for_wav_playback(path, duration_seconds, interrupt_pressed)


def play_wav_chunk(
    path: str | Path,
    duration_seconds: Callable[[str | Path], float],
    interrupt_pressed: Callable[[], bool],
) -> bool:
    play_wav_async(path)
    return wait_for_wav_playback(path, duration_seconds, interrupt_pressed)
