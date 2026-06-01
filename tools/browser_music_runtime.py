from __future__ import annotations

import os
import time
import webbrowser
from collections.abc import Callable
from dataclasses import dataclass, field

from tools.browser_music import BrowserMusic
from tools.spotify_ui_automation import SpotifyUiAutomation
from tools.system_tools import focus_app as default_focus_app


def _default_startfile() -> Callable[[str], object]:
    return getattr(os, "startfile", webbrowser.open)


@dataclass
class BrowserMusicRuntime:
    normalize_text: Callable[[str], str]
    run_powershell: Callable[..., object]
    click: Callable[..., None]
    set_cursor_pos: Callable[[int, int], object]
    sleep: Callable[[float], None] = time.sleep
    focus_app: Callable[[str], object] = default_focus_app
    open_url: Callable[..., object] = webbrowser.open
    os_startfile: Callable[[str], object] = field(default_factory=_default_startfile)
    _spotify_ui: SpotifyUiAutomation | None = field(default=None, init=False, repr=False)
    _browser_music: BrowserMusic | None = field(default=None, init=False, repr=False)

    def spotify_ui(self) -> SpotifyUiAutomation:
        if self._spotify_ui is None:
            self._spotify_ui = SpotifyUiAutomation(
                run_powershell=self.run_powershell,
                click=self.click,
                set_cursor_pos=self.set_cursor_pos,
                sleep=self.sleep,
                focus_app=self.focus_app,
            )
        return self._spotify_ui

    def browser_music(self) -> BrowserMusic:
        if self._browser_music is None:
            self._browser_music = BrowserMusic(
                normalize_text=self.normalize_text,
                os_startfile=self.os_startfile,
                sleep=self.sleep,
                focus_app=self.focus_app,
                open_url=self.open_url,
                click_track_by_name=self.spotify_ui().click_track_by_name,
                click_first_visible_track=self.spotify_ui().click_first_visible_track,
            )
        return self._browser_music

    def spotify_diagnostic(self) -> str:
        return self.spotify_ui().diagnostic()

    def search_music(self, service: str, query: str) -> str:
        return self.browser_music().search_music(service, query)

    def surprise_music(self, service: str = "spotify") -> str:
        return self.browser_music().surprise_music(service)

    def music_session(self, service: str = "spotify", vibe: str = "") -> str:
        return self.browser_music().music_session(service, vibe)

    def queue_music(self, service: str, query: str) -> str:
        return self.browser_music().queue_music(service, query)

    def like_current_track(self) -> str:
        return self.browser_music().like_current_track()

    def dislike_current_track(self) -> str:
        return self.browser_music().dislike_current_track()

    def more_like_current_track(self) -> str:
        return self.browser_music().more_like_current_track()

    def less_music_vibe(self, vibe: str = "") -> str:
        return self.browser_music().less_music_vibe(vibe)
