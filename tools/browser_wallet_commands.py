from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class BrowserWalletCommands:
    private_wallet_url: str
    default_wallet_url: str
    configured_wallet_url: str
    open_url_in_wallet_browser: Callable[[str], str | None]
    read_full_page_text_from_foreground: Callable[..., str | None]
    read_full_page_text_from_browser: Callable[..., str | None]
    click_browser_element_by_text: Callable[..., bool]
    activate_window_names: Callable[[list[str]], bool]
    shortcut: Callable[..., None]
    browser_close_tab: Callable[[], str]
    parse_wallet_text_blob: Callable[[str, str], dict]
    refresh_wallet_snapshot_auto: Callable[..., dict]
    format_public_wallet_refresh_result: Callable[..., str]
    webbrowser_open: Callable[..., object]
    investment_snapshot: Callable[[], str]
    vk_control: int
    vk_w: int
    sleep: Callable[[float], None] = time.sleep
    now: Callable[[], float] = time.time

    def visible_capture_summary(
        self,
        url: str,
        close_tab: bool = True,
        max_seconds: float = 12.0,
        sections: tuple[str, ...] = ("Patrimonio",),
        section_delay: float = 1.4,
    ):
        app_name = self.open_url_in_wallet_browser(url)
        if app_name is None:
            return None

        deadline = self.now() + max(4.0, float(max_seconds or 12.0))
        self.sleep(3.2)

        try:
            captured_text = self._read_visible_wallet_text(app_name)
            if not captured_text:
                return None

            extra_sections = []
            for section_label in sections:
                if self.now() >= deadline:
                    break
                try:
                    if self.click_browser_element_by_text(section_label, app_names=[app_name] if app_name else None):
                        self.sleep(min(section_delay, max(0.2, deadline - self.now())))
                        section_text = str(self.read_full_page_text_from_foreground(wait_seconds=0.55) or "").strip()
                        if section_text and section_text not in captured_text:
                            extra_sections.append(section_text)
                except Exception:
                    continue

            if extra_sections:
                captured_text = "\n".join([captured_text, *extra_sections])

            snapshot = self.parse_wallet_text_blob(captured_text, url)
            summary = str(snapshot.get("summary", "")).strip()
            if not summary:
                return "Carteira lida pela aba visivel e memoria atualizada."
            return summary
        except Exception:
            return None
        finally:
            if close_tab:
                self._close_wallet_tab(app_name)

    def visible_capture_summary_legacy(self, url: str, close_tab: bool = True):
        return self.visible_capture_summary(
            url,
            close_tab=close_tab,
            max_seconds=12.0,
            sections=("Patrimonio", "Proventos"),
            section_delay=2.0,
        )

    def open_wallet_and_summarize(self) -> str:
        private_wallet_url = str(self.private_wallet_url or "").strip()
        if private_wallet_url and "/wallet/" in private_wallet_url.lower():
            visible_summary = self.visible_capture_summary(private_wallet_url, close_tab=True)
            if visible_summary:
                return "Abri sua carteira do Investidor10. " + visible_summary

        if self.default_wallet_url and "/wallet/" in self.default_wallet_url:
            try:
                snapshot = self.refresh_wallet_snapshot_auto(force=True)
                summary = str(snapshot.get("summary", "")).strip() or self.format_public_wallet_refresh_result(force=True)
                return "Abri sua carteira do Investidor10. " + summary
            except Exception:
                visible_summary = self.visible_capture_summary(self.default_wallet_url, close_tab=True)
                if visible_summary:
                    return "Abri sua carteira do Investidor10. " + visible_summary

        self.webbrowser_open(self.default_wallet_url)
        self.sleep(1.5)
        self.sleep(1.0)
        summary = self.investment_snapshot()
        if self.configured_wallet_url:
            return "Abri sua carteira do Investidor10. " + summary
        return (
            "Abri a area da carteira do Investidor10. "
            + summary
            + " Para abrir direto no seu link, configure AXEL_INVESTIDOR10_WALLET_URL no arquivo .env."
        )

    def _read_visible_wallet_text(self, app_name: str) -> str:
        captured_text = str(self.read_full_page_text_from_foreground(wait_seconds=0.55) or "").strip()
        if not captured_text or not self._looks_like_wallet_text(captured_text):
            captured_text = str(self.read_full_page_text_from_browser(wait_seconds=0.55) or "").strip()
        if (not captured_text or not self._looks_like_wallet_text(captured_text)) and app_name:
            captured_text = str(self.read_full_page_text_from_browser(wait_seconds=0.55, app_name=app_name) or "").strip()
        return captured_text

    @staticmethod
    def _looks_like_wallet_text(text: str) -> bool:
        compact = str(text or "").lower()
        return (
            "patrimonio total" in compact
            or "patrimônio total" in compact
            or "patrimônio total" in compact
        )

    def _close_wallet_tab(self, app_name: str):
        try:
            if app_name:
                if self.activate_window_names([app_name]):
                    self.shortcut(self.vk_control, self.vk_w)
            else:
                self.browser_close_tab()
        except Exception:
            pass
