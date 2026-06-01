from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from tools.browser_javascript import run_browser_javascript, run_browser_javascript_and_read_clipboard
from tools.browser_product_cards import read_product_cards_via_javascript


@dataclass
class BrowserJavascriptRuntime:
    activate_browser_window: Callable[[], bool]
    get_clipboard_text: Callable[[], str]
    set_clipboard_text: Callable[[str], None]
    shortcut: Callable[..., None]
    type_text: Callable[[str], None]
    tap: Callable[[int], None]
    vk_control: int
    vk_l: int
    vk_v: int
    vk_return: int
    sleep: Callable[[float], None] = time.sleep

    def run_javascript(self, script_body: str) -> bool:
        return run_browser_javascript(
            script_body,
            activate_browser_window=self.activate_browser_window,
            get_clipboard_text=self.get_clipboard_text,
            set_clipboard_text=self.set_clipboard_text,
            shortcut=self.shortcut,
            type_text=self.type_text,
            tap=self.tap,
            sleep=self.sleep,
            vk_control=self.vk_control,
            vk_l=self.vk_l,
            vk_v=self.vk_v,
            vk_return=self.vk_return,
        )

    def run_javascript_and_read_clipboard(self, script_body: str, marker: str, timeout: float = 0.8) -> str:
        return run_browser_javascript_and_read_clipboard(
            script_body,
            marker,
            activate_browser_window=self.activate_browser_window,
            get_clipboard_text=self.get_clipboard_text,
            set_clipboard_text=self.set_clipboard_text,
            shortcut=self.shortcut,
            type_text=self.type_text,
            tap=self.tap,
            sleep=self.sleep,
            vk_control=self.vk_control,
            vk_l=self.vk_l,
            vk_v=self.vk_v,
            vk_return=self.vk_return,
            timeout=timeout,
        )

    def read_product_cards(self, limit: int = 10):
        return read_product_cards_via_javascript(
            run_javascript_and_read_clipboard=self.run_javascript_and_read_clipboard,
            limit=limit,
        )
