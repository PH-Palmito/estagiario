from __future__ import annotations

import ctypes
import time

from tools.browser_windows_io import BrowserWindowsIO

BROWSER_ACTIVATE_NAMES = ["chrome", "msedge", "firefox", "opera", "brave"]

VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_TAB = 0x09
VK_A = 0x41
VK_C = 0x43
VK_ESCAPE = 0x1B
VK_L = 0x4C
VK_V = 0x56
VK_W = 0x57
VK_F = 0x46
VK_R = 0x52
VK_F5 = 0x74
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D
VK_0 = 0x30
VK_BACK = 0x08
VK_RETURN = 0x0D
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_SPACE = 0x20
VK_DOWN = 0x28
VK_UP = 0x26
VK_LEFT = 0x25
VK_RIGHT = 0x27

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800

user32 = ctypes.windll.user32
try:
    # Keeps UI Automation coordinates aligned with mouse coordinates on scaled/multi-monitor setups.
    user32.SetProcessDPIAware()
except Exception:
    pass

_BROWSER_WINDOWS_IO = None


def browser_windows_io() -> BrowserWindowsIO:
    global _BROWSER_WINDOWS_IO
    if _BROWSER_WINDOWS_IO is None:
        _BROWSER_WINDOWS_IO = BrowserWindowsIO(
            user32=user32,
            browser_names=BROWSER_ACTIVATE_NAMES,
            keyup_flag=KEYEVENTF_KEYUP,
            leftdown_flag=MOUSEEVENTF_LEFTDOWN,
            leftup_flag=MOUSEEVENTF_LEFTUP,
            sleep=time.sleep,
        )
    return _BROWSER_WINDOWS_IO
