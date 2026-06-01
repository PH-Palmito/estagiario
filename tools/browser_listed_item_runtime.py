from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field

from tools.browser_listed_items import (
    BrowserListedItemCommands,
    click_browser_item_from_text as click_browser_item_from_text_command,
)


@dataclass
class BrowserListedItemRuntime:
    activate_browser_window: Callable[[], bool]
    refresh_browser_context: Callable[[], str]
    listed_browser_elements: Callable[[], list]
    describe_screen: Callable[[], str]
    click_page_item_by_text: Callable[[str], bool]
    click_browser_element_by_text: Callable[[str], bool]
    browser_find: Callable[[str], str]
    click: Callable[[int, int], None]
    sleep: Callable[[float], None] = time.sleep
    _commands: BrowserListedItemCommands | None = field(default=None, init=False, repr=False)

    def click_browser_item_from_text(self, text: str) -> bool:
        return click_browser_item_from_text_command(text, self.click_browser_element_by_text)

    def commands(self) -> BrowserListedItemCommands:
        if self._commands is None:
            self._commands = BrowserListedItemCommands(
                activate_browser_window=self.activate_browser_window,
                refresh_browser_context=self.refresh_browser_context,
                listed_browser_elements=self.listed_browser_elements,
                describe_screen=self.describe_screen,
                click_page_item_by_text=self.click_page_item_by_text,
                click_browser_item_from_text=self.click_browser_item_from_text,
                browser_find=self.browser_find,
                click=self.click,
                sleep=self.sleep,
            )
        return self._commands

    def click_listed_item(self, index: int) -> str:
        return self.commands().click_listed_item(index)

    def describe_listed_item(self, index: int) -> str:
        return self.commands().describe_listed_item(index)

    def cheapest_listed_item(self) -> str:
        return self.commands().cheapest_listed_item()
