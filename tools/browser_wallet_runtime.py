from __future__ import annotations

import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field

from config import INVESTIDOR10_PRIVATE_WALLET_URL, INVESTIDOR10_WALLET_URL
from memory.public_wallet_refresh import (
    format_public_wallet_refresh_result,
    parse_wallet_text_blob,
    refresh_wallet_snapshot_auto,
)
from tools.browser_wallet_commands import BrowserWalletCommands


DEFAULT_INVESTIDOR10_WALLET_URL = (
    INVESTIDOR10_WALLET_URL
    or INVESTIDOR10_PRIVATE_WALLET_URL
    or "https://investidor10.com.br/wallet/my-wallet"
)


@dataclass
class BrowserWalletRuntime:
    open_url_in_wallet_browser: Callable[[str], str | None]
    read_full_page_text_from_foreground: Callable[..., str | None]
    read_full_page_text_from_browser: Callable[..., str | None]
    click_browser_element_by_text: Callable[..., bool]
    activate_window_names: Callable[[list[str]], bool]
    shortcut: Callable[..., None]
    browser_close_tab: Callable[[], str]
    investment_snapshot: Callable[[], str]
    vk_control: int
    vk_w: int
    private_wallet_url: str = INVESTIDOR10_PRIVATE_WALLET_URL
    default_wallet_url: str = DEFAULT_INVESTIDOR10_WALLET_URL
    configured_wallet_url: str = INVESTIDOR10_WALLET_URL
    parse_wallet_text_blob: Callable[[str, str], dict] = parse_wallet_text_blob
    refresh_wallet_snapshot_auto: Callable[..., dict] = refresh_wallet_snapshot_auto
    format_public_wallet_refresh_result: Callable[..., str] = format_public_wallet_refresh_result
    webbrowser_open: Callable[..., object] = webbrowser.open
    sleep: Callable[[float], None] = time.sleep
    now: Callable[[], float] = time.time
    _commands: BrowserWalletCommands | None = field(default=None, init=False, repr=False)

    def commands(self) -> BrowserWalletCommands:
        if self._commands is None:
            self._commands = BrowserWalletCommands(
                private_wallet_url=self.private_wallet_url,
                default_wallet_url=self.default_wallet_url,
                configured_wallet_url=self.configured_wallet_url,
                open_url_in_wallet_browser=self.open_url_in_wallet_browser,
                read_full_page_text_from_foreground=self.read_full_page_text_from_foreground,
                read_full_page_text_from_browser=self.read_full_page_text_from_browser,
                click_browser_element_by_text=self.click_browser_element_by_text,
                activate_window_names=self.activate_window_names,
                shortcut=self.shortcut,
                browser_close_tab=self.browser_close_tab,
                parse_wallet_text_blob=self.parse_wallet_text_blob,
                refresh_wallet_snapshot_auto=self.refresh_wallet_snapshot_auto,
                format_public_wallet_refresh_result=self.format_public_wallet_refresh_result,
                webbrowser_open=self.webbrowser_open,
                investment_snapshot=self.investment_snapshot,
                vk_control=self.vk_control,
                vk_w=self.vk_w,
                sleep=self.sleep,
                now=self.now,
            )
        return self._commands

    def visible_capture_summary_legacy(self, url: str, close_tab: bool = True):
        return self.commands().visible_capture_summary_legacy(url, close_tab=close_tab)

    def visible_capture_summary(self, url: str, close_tab: bool = True, max_seconds: float = 12.0):
        return self.commands().visible_capture_summary(
            url,
            close_tab=close_tab,
            max_seconds=max_seconds,
        )

    def open_wallet_and_summarize(self) -> str:
        return self.commands().open_wallet_and_summarize()
