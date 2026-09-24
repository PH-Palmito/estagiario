from __future__ import annotations

import ctypes
import sys
from collections.abc import Callable

try:
    import winsound
except ImportError:
    winsound = None

VIRTUAL_KEYS = {
    "ESC": 0x1B,
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
}

_user32 = ctypes.windll.user32 if sys.platform.startswith("win") else None
_last_key_down: dict[int, bool] = {}


def hotkey_name(preferences: dict, key: str, default: str) -> str:
    return str(preferences.get(key, default)).upper()


def hotkey_vk(name: str, default: str) -> int:
    return VIRTUAL_KEYS.get(name, VIRTUAL_KEYS[default])


def speech_interrupt_keys(hotkey_vk: int, toggle_vk: int) -> set[int]:
    return {hotkey_vk, toggle_vk, VIRTUAL_KEYS["ESC"]}


def consume_key_press(
    vk_code: int,
    *,
    key_state: dict[int, bool] | None = None,
    get_async_key_state: Callable[[int], int] | None = None,
) -> bool:
    state = _last_key_down if key_state is None else key_state
    if get_async_key_state is None and _user32 is None:
        return False
    get_state = _user32.GetAsyncKeyState if get_async_key_state is None else get_async_key_state
    was_down = state.get(vk_code, False)
    is_down = bool(get_state(vk_code) & 0x8000)
    pressed_now = is_down and not was_down
    state[vk_code] = is_down
    return pressed_now


def play_activation_sound(preferences: dict):
    if not bool(preferences.get("activation_sound", True)):
        return

    try:
        if winsound is None:
            return
        hz = int(preferences.get("activation_sound_hz", 880))
        duration = int(preferences.get("activation_sound_ms", 120))
        winsound.Beep(hz, duration)
    except Exception:
        try:
            winsound.PlaySound("SystemAsterisk", winsound.SND_ALIAS | winsound.SND_ASYNC)
        except Exception:
            try:
                winsound.MessageBeep(winsound.MB_OK)
            except Exception:
                pass
