from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class BrowserTextReader:
    activate_browser_window: Callable[[], bool]
    activate_window_names: Callable[[list[str]], bool]
    get_clipboard_text: Callable[[], str]
    set_clipboard_text: Callable[[str], None]
    shortcut: Callable[..., None]
    tap: Callable[[int], None]
    sleep: Callable[[float], None]
    vk_control: int
    vk_c: int
    vk_a: int
    vk_escape: int

    def read_selected_text(self, app_name: str | None = None):
        if app_name:
            if not self.activate_window_names([app_name]):
                return None
        elif not self.activate_browser_window():
            return None

        old_clipboard = self.get_clipboard_text()
        try:
            self.set_clipboard_text("")
            self.shortcut(self.vk_control, self.vk_c)
            self.sleep(0.25)
            return self.get_clipboard_text()
        finally:
            self.set_clipboard_text(old_clipboard)

    def read_full_page_text_from_browser(self, wait_seconds: float = 0.35, app_name: str | None = None):
        if app_name:
            if not self.activate_window_names([app_name]):
                return None
        elif not self.activate_browser_window():
            return None
        return self._read_full_page_text(wait_seconds)

    def read_full_page_text_from_foreground(self, wait_seconds: float = 0.35):
        return self._read_full_page_text(wait_seconds)

    def _read_full_page_text(self, wait_seconds: float):
        old_clipboard = self.get_clipboard_text()
        try:
            self.set_clipboard_text("")
            self.shortcut(self.vk_control, self.vk_a)
            self.sleep(0.12)
            self.shortcut(self.vk_control, self.vk_c)
            self.sleep(wait_seconds)
            return self.get_clipboard_text()
        finally:
            self.tap(self.vk_escape)
            self.set_clipboard_text(old_clipboard)


def compact_selected_text(text: str, max_length: int = 650):
    compact = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(compact) <= max_length:
        return compact
    return compact[: max(0, max_length - 3)].rstrip() + "..."
