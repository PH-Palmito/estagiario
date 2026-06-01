from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from tools.browser_selection_commands import BrowserSelectionCommands
from tools.browser_text_reader import BrowserTextReader, compact_selected_text


@dataclass
class BrowserTextRuntime:
    activate_browser_window: Callable[[], bool]
    activate_window_names: Callable[[list[str]], bool]
    get_clipboard_text: Callable[[], str]
    set_clipboard_text: Callable[[str], None]
    shortcut: Callable[..., None]
    tap: Callable[[int], None]
    sleep: Callable[[float], None]
    clear_browser_snapshot: Callable[..., None]
    set_last_selected_text: Callable[[str], None]
    last_selected_text: Callable[[], str]
    remember_browser_analysis: Callable[..., None]
    remember_text_items: Callable[..., None]
    selected_text_items: Callable[..., list[str]]
    ask_model: Callable[..., str]
    vk_control: int
    vk_c: int
    vk_a: int
    vk_escape: int
    _text_reader: BrowserTextReader | None = field(default=None, init=False, repr=False)
    _selection_commands: BrowserSelectionCommands | None = field(default=None, init=False, repr=False)

    def text_reader(self) -> BrowserTextReader:
        if self._text_reader is None:
            self._text_reader = BrowserTextReader(
                activate_browser_window=self.activate_browser_window,
                activate_window_names=self.activate_window_names,
                get_clipboard_text=self.get_clipboard_text,
                set_clipboard_text=self.set_clipboard_text,
                shortcut=self.shortcut,
                tap=self.tap,
                sleep=self.sleep,
                vk_control=self.vk_control,
                vk_c=self.vk_c,
                vk_a=self.vk_a,
                vk_escape=self.vk_escape,
            )
        return self._text_reader

    def selection_commands(self) -> BrowserSelectionCommands:
        if self._selection_commands is None:
            self._selection_commands = BrowserSelectionCommands(
                read_selected_text_from_browser=self.read_selected_text,
                compact_selected_text=self.compact_selected_text,
                clear_browser_snapshot=self.clear_browser_snapshot,
                set_last_selected_text=self.set_last_selected_text,
                last_selected_text=self.last_selected_text,
                remember_browser_analysis=self.remember_browser_analysis,
                remember_text_items=self.remember_text_items,
                selected_text_items=self.selected_text_items,
                ask_model=self.ask_model,
            )
        return self._selection_commands

    def read_selected_text(self, app_name: str | None = None):
        return self.text_reader().read_selected_text(app_name=app_name)

    def read_full_page_text_from_browser(self, wait_seconds: float = 0.35, app_name: str | None = None):
        return self.text_reader().read_full_page_text_from_browser(wait_seconds=wait_seconds, app_name=app_name)

    def read_full_page_text_from_foreground(self, wait_seconds: float = 0.35):
        return self.text_reader().read_full_page_text_from_foreground(wait_seconds=wait_seconds)

    def compact_selected_text(self, text: str, max_length: int = 650):
        return compact_selected_text(text, max_length=max_length)

    def read_selection(self) -> str:
        return self.selection_commands().read_selection()

    def translate_selection(self) -> str:
        return self.selection_commands().translate_selection()

    def translate_last_selection(self) -> str:
        return self.selection_commands().translate_last_selection()

    def read_selected_products(self) -> str:
        return self.selection_commands().read_selected_products()
