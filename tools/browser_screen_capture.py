from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from tools.browser_page_text import rank_page_text_lines, useful_page_text_lines
from tools.browser_screen_analysis import (
    detect_screen_category,
    merge_screen_lines,
    screen_lines_quality,
)
from tools.browser_screen_narrative import items_are_navigation_heavy


@dataclass
class BrowserScreenCapture:
    activate_browser_window: Callable[[], bool]
    get_clipboard_text: Callable[[], str]
    set_clipboard_text: Callable[[str], None]
    shortcut: Callable[..., None]
    tap: Callable[[int], None]
    read_browser_elements: Callable[[int], list | None]
    browser_context_recently_changed: Callable[..., bool]
    vk_control: int
    vk_a: int
    vk_c: int
    vk_escape: int
    vk_l: int
    sleep: Callable[[float], None] = time.sleep
    monotonic_ns: Callable[[], int] = time.monotonic_ns

    def get_browser_url(self) -> str:
        if not self.activate_browser_window():
            return ""

        old_clipboard = self.get_clipboard_text()
        sentinel = f"__ESTAGIARIO_BROWSER_URL__{self.monotonic_ns()}__"
        copied = ""

        try:
            self.set_clipboard_text(sentinel)
            self.sleep(0.03)
            self.shortcut(self.vk_control, self.vk_l)
            self.sleep(0.08)
            self.shortcut(self.vk_control, self.vk_c)
            for _ in range(12):
                self.sleep(0.08)
                sample = self.get_clipboard_text().strip()
                if sample and sample != sentinel and sample != old_clipboard:
                    copied = sample
                    break
        finally:
            self.tap(self.vk_escape)
            self.set_clipboard_text(old_clipboard)

        if not copied:
            return ""

        if copied.startswith(("http://", "https://")):
            return copied

        return ""

    def read_page_text_via_clipboard(self, limit: int = 10, page_url: str = "", page_title: str = ""):
        old_clipboard = self.get_clipboard_text()
        copied = ""
        sentinel = f"__ESTAGIARIO_READ_PAGE__{self.monotonic_ns()}__"
        last_sample = ""
        stable_reads = 0

        try:
            self.set_clipboard_text(sentinel)
            self.sleep(0.03)
            self.shortcut(self.vk_control, self.vk_a)
            self.sleep(0.12)
            self.shortcut(self.vk_control, self.vk_c)
            for _ in range(18):
                self.sleep(0.12)
                sample = self.get_clipboard_text()
                stripped = sample.strip()
                if not stripped or stripped == sentinel or sample == old_clipboard:
                    stable_reads = 0
                    continue

                copied = sample
                if sample == last_sample:
                    stable_reads += 1
                else:
                    last_sample = sample
                    stable_reads = 1

                if stable_reads >= 2 and len(stripped) >= 20:
                    break
        finally:
            self.tap(self.vk_escape)
            self.set_clipboard_text(old_clipboard)

        ranked_lines = rank_page_text_lines(copied, limit=limit, page_url=page_url, page_title=page_title)
        if ranked_lines:
            return ranked_lines

        return useful_page_text_lines(copied, limit=limit, page_url=page_url, page_title=page_title)

    def read_screen_content_lines(
        self,
        item_limit: int,
        page_limit: int,
        page_url: str,
        page_title: str,
    ):
        items = self.read_browser_elements(item_limit) or []
        item_lines = [item["text"] for item in items]
        item_quality = screen_lines_quality(item_lines)
        category = detect_screen_category([], page_url=page_url, page_title=page_title)
        prefer_page_text = (
            not items
            or items_are_navigation_heavy(item_lines, page_url=page_url, page_title=page_title)
            or item_quality < 24
            or category in {"financas", "noticia"}
        )

        page_lines = []
        best_page_score = 0
        if prefer_page_text:
            if self.browser_context_recently_changed():
                self.sleep(0.35)

            first_pass = self.read_page_text_via_clipboard(limit=page_limit, page_url=page_url, page_title=page_title)
            page_lines = first_pass
            best_page_score = screen_lines_quality(first_pass)

            need_second_pass = self.browser_context_recently_changed(2.0) or not first_pass or best_page_score < 24
            if need_second_pass:
                self.sleep(0.25)
                second_pass = self.read_page_text_via_clipboard(limit=page_limit, page_url=page_url, page_title=page_title)
                second_score = screen_lines_quality(second_pass)
                if second_score > best_page_score:
                    page_lines = second_pass
                    best_page_score = second_score

        combined_lines = merge_screen_lines(page_lines, item_lines, limit=max(item_limit, page_limit))
        combined_quality = screen_lines_quality(combined_lines)

        return {
            "items": items,
            "item_lines": item_lines,
            "item_quality": item_quality,
            "page_lines": page_lines,
            "page_quality": best_page_score,
            "combined_lines": combined_lines,
            "combined_quality": combined_quality,
            "prefer_page_text": prefer_page_text,
        }
