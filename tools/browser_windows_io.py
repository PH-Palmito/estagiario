from __future__ import annotations

import ctypes
import subprocess
import time
from dataclasses import dataclass
from typing import Sequence

from tools.windows_input import click as windows_click
from tools.windows_input import shortcut as windows_shortcut
from tools.windows_input import tap as windows_tap
from tools.windows_input import tap_times as windows_tap_times
from tools.windows_input import type_text as windows_type_text
from tools.windows_shell import POWERSHELL_EXE
from tools.windows_shell import activate_window_names as windows_activate_window_names
from tools.windows_shell import get_clipboard_text as windows_get_clipboard_text
from tools.windows_shell import run_powershell as windows_run_powershell
from tools.windows_shell import set_clipboard_text as windows_set_clipboard_text
from tools.windows_window import app_window_rect as windows_app_window_rect
from tools.windows_window import first_window_rect as windows_first_window_rect
from tools.windows_window import foreground_window_capture_hash as windows_foreground_window_capture_hash
from tools.windows_window import foreground_window_rect as windows_foreground_window_rect
from tools.windows_window import foreground_window_title as windows_foreground_window_title


@dataclass
class BrowserWindowsIO:
    user32: object
    browser_names: Sequence[str]
    keyup_flag: int
    leftdown_flag: int
    leftup_flag: int
    powershell_exe: str = POWERSHELL_EXE
    sleep: object = time.sleep

    def run_powershell(self, script: str, timeout_seconds: int = 10) -> subprocess.CompletedProcess:
        return windows_run_powershell(script, timeout_seconds=timeout_seconds)

    def get_clipboard_text(self) -> str:
        return windows_get_clipboard_text(run_powershell_func=self.run_powershell)

    def set_clipboard_text(self, text: str) -> None:
        windows_set_clipboard_text(text, powershell_exe=self.powershell_exe)

    def activate_window_names(self, names) -> bool:
        return windows_activate_window_names(names, run_powershell_func=self.run_powershell)

    def activate_browser_window(self) -> bool:
        return self.activate_window_names(self.browser_names)

    def tap(self, vk_code: int) -> None:
        windows_tap(vk_code, keybd_event=self.user32.keybd_event, keyup_flag=self.keyup_flag, sleep=self.sleep)

    def tap_times(self, vk_code: int, times: int, delay: float = 0.08) -> None:
        windows_tap_times(
            vk_code,
            times,
            delay=delay,
            keybd_event=self.user32.keybd_event,
            keyup_flag=self.keyup_flag,
            sleep=self.sleep,
        )

    def click(self, x: int, y: int, clicks: int = 1) -> None:
        windows_click(
            x,
            y,
            clicks=clicks,
            set_cursor_pos=self.user32.SetCursorPos,
            mouse_event=self.user32.mouse_event,
            leftdown_flag=self.leftdown_flag,
            leftup_flag=self.leftup_flag,
            sleep=self.sleep,
        )

    def shortcut(self, *vk_codes: int) -> None:
        windows_shortcut(*vk_codes, keybd_event=self.user32.keybd_event, keyup_flag=self.keyup_flag, sleep=self.sleep)

    def type_text(self, text: str, *, vk_shift: int) -> None:
        self.user32.VkKeyScanW.restype = ctypes.c_short
        windows_type_text(
            text,
            vk_key_scan=self.user32.VkKeyScanW,
            keybd_event=self.user32.keybd_event,
            tap_func=self.tap,
            vk_shift=vk_shift,
            keyup_flag=self.keyup_flag,
            sleep=self.sleep,
        )

    def foreground_window_title(self) -> str:
        return windows_foreground_window_title(self.user32)

    def foreground_window_rect(self):
        return windows_foreground_window_rect(self.user32)

    def foreground_window_capture_hash(self) -> str:
        return windows_foreground_window_capture_hash(
            get_rect_func=self.foreground_window_rect,
            run_powershell_func=self.run_powershell,
        )

    def app_window_rect(self, app_name: str):
        return windows_app_window_rect(app_name, run_powershell_func=self.run_powershell)

    def browser_window_rect(self):
        return windows_first_window_rect(self.browser_names, get_app_window_rect_func=self.app_window_rect)
