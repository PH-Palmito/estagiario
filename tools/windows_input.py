from __future__ import annotations

import time

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004


def tap(vk_code: int, *, keybd_event, keyup_flag: int = KEYEVENTF_KEYUP, sleep=time.sleep) -> None:
    keybd_event(vk_code, 0, 0, 0)
    sleep(0.02)
    keybd_event(vk_code, 0, keyup_flag, 0)


def tap_times(
    vk_code: int,
    times: int,
    delay: float = 0.08,
    *,
    keybd_event,
    keyup_flag: int = KEYEVENTF_KEYUP,
    sleep=time.sleep,
) -> None:
    for _ in range(max(1, times)):
        tap(vk_code, keybd_event=keybd_event, keyup_flag=keyup_flag, sleep=sleep)
        sleep(delay)


def click(
    x: int,
    y: int,
    clicks: int = 1,
    *,
    set_cursor_pos,
    mouse_event,
    leftdown_flag: int = MOUSEEVENTF_LEFTDOWN,
    leftup_flag: int = MOUSEEVENTF_LEFTUP,
    sleep=time.sleep,
) -> None:
    set_cursor_pos(int(x), int(y))
    sleep(0.05)

    for _ in range(max(1, clicks)):
        mouse_event(leftdown_flag, 0, 0, 0, 0)
        sleep(0.03)
        mouse_event(leftup_flag, 0, 0, 0, 0)
        sleep(0.12)


def shortcut(*vk_codes: int, keybd_event, keyup_flag: int = KEYEVENTF_KEYUP, sleep=time.sleep) -> None:
    for code in vk_codes:
        keybd_event(code, 0, 0, 0)
        sleep(0.02)

    sleep(0.04)

    for code in reversed(vk_codes):
        keybd_event(code, 0, keyup_flag, 0)
        sleep(0.02)


def type_text(
    text: str,
    *,
    vk_key_scan,
    keybd_event,
    tap_func,
    vk_shift: int,
    keyup_flag: int = KEYEVENTF_KEYUP,
    sleep=time.sleep,
) -> None:
    for char in text:
        key = vk_key_scan(ord(char))
        vk_code = key & 0xFF
        shift_state = (key >> 8) & 0xFF

        if vk_code == 0xFF:
            continue

        modifiers = []
        if shift_state & 1:
            modifiers.append(vk_shift)

        for mod in modifiers:
            keybd_event(mod, 0, 0, 0)
            sleep(0.01)

        tap_func(vk_code)

        for mod in reversed(modifiers):
            keybd_event(mod, 0, keyup_flag, 0)
            sleep(0.01)
