from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from tools.browser_screen_capture import BrowserScreenCapture
from tools.browser_screen_commands import BrowserScreenCommands


DEFAULT_SCREEN_INTROS = (
    "Resumo da tela",
    "Panorama da tela",
    "Visao rapida da tela",
)


@dataclass
class BrowserScreenRuntime:
    activate_browser_window: Callable[[], bool]
    refresh_browser_context: Callable[[], str]
    get_clipboard_text: Callable[[], str]
    set_clipboard_text: Callable[[str], None]
    shortcut: Callable[..., None]
    tap: Callable[[int], None]
    read_browser_elements: Callable[[int], list | None]
    browser_context_recently_changed: Callable[..., bool]
    get_foreground_window_title: Callable[[], str]
    clean_browser_title: Callable[[str], str]
    clear_browser_snapshot: Callable[..., None]
    set_browser_elements: Callable[..., None]
    remember_text_items: Callable[..., None]
    remember_browser_analysis: Callable[..., None]
    save_investment_snapshot: Callable[..., None]
    vk_control: int
    vk_a: int
    vk_c: int
    vk_escape: int
    vk_l: int
    sleep: Callable[[float], None]
    intros: Sequence[str] = DEFAULT_SCREEN_INTROS
    random_choice: Callable[[Sequence[str]], str] = random.choice
    _screen_capture: BrowserScreenCapture | None = field(default=None, init=False, repr=False)
    _screen_commands: BrowserScreenCommands | None = field(default=None, init=False, repr=False)

    def screen_summary_intro(self) -> str:
        return self.random_choice(self.intros)

    def screen_capture(self) -> BrowserScreenCapture:
        if self._screen_capture is None:
            self._screen_capture = BrowserScreenCapture(
                activate_browser_window=self.activate_browser_window,
                get_clipboard_text=self.get_clipboard_text,
                set_clipboard_text=self.set_clipboard_text,
                shortcut=self.shortcut,
                tap=self.tap,
                read_browser_elements=self.read_browser_elements,
                browser_context_recently_changed=self.browser_context_recently_changed,
                vk_control=self.vk_control,
                vk_a=self.vk_a,
                vk_c=self.vk_c,
                vk_escape=self.vk_escape,
                vk_l=self.vk_l,
                sleep=self.sleep,
            )
        return self._screen_capture

    def screen_commands(self) -> BrowserScreenCommands:
        if self._screen_commands is None:
            self._screen_commands = BrowserScreenCommands(
                activate_browser_window=self.activate_browser_window,
                refresh_browser_context=self.refresh_browser_context,
                get_browser_url=self.get_browser_url,
                get_page_title=lambda: self.clean_browser_title(self.get_foreground_window_title()),
                read_screen_content_lines=self.read_screen_content_lines,
                clear_browser_snapshot=self.clear_browser_snapshot,
                set_browser_elements=self.set_browser_elements,
                remember_text_items=self.remember_text_items,
                remember_browser_analysis=self.remember_browser_analysis,
                screen_summary_intro=self.screen_summary_intro,
                save_investment_snapshot=self.save_investment_snapshot,
            )
        return self._screen_commands

    def get_browser_url(self) -> str:
        return self.screen_capture().get_browser_url()

    def read_screen_content_lines(
        self,
        item_limit: int,
        page_limit: int,
        page_url: str,
        page_title: str,
    ):
        return self.screen_capture().read_screen_content_lines(
            item_limit=item_limit,
            page_limit=page_limit,
            page_url=page_url,
            page_title=page_title,
        )

    def read_page_text_via_clipboard(self, limit: int = 10, page_url: str = "", page_title: str = ""):
        return self.screen_capture().read_page_text_via_clipboard(
            limit=limit,
            page_url=page_url,
            page_title=page_title,
        )

    def summarize_screen(self) -> str:
        return self.screen_commands().summarize_screen()

    def explain_screen(self) -> str:
        return self.screen_commands().explain_screen()

    def investment_snapshot(self) -> str:
        return self.screen_commands().investment_snapshot()

    def describe_screen(self) -> str:
        return self.screen_commands().describe_screen()
