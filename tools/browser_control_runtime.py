from __future__ import annotations

import time
import webbrowser
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from tools.browser_controls import BrowserControls
from tools.browser_ui_automation import BrowserUiAutomation, normalize_ui_text


@dataclass
class BrowserControlRuntime:
    browser_names: list[str]
    activate_browser_window: Callable[[], bool]
    run_powershell: Callable[..., object]
    shortcut: Callable[..., None]
    tap: Callable[[int], None]
    click: Callable[..., None]
    get_browser_window_rect: Callable[[], tuple[int, int, int, int] | None]
    type_text: Callable[[str], None]
    keybd_event: Callable[..., None]
    mouse_event: Callable[..., None]
    keyup_flag: int
    mouse_wheel_flag: int
    vk_control: int
    vk_shift: int
    vk_menu: int
    vk_tab: int
    vk_w: int
    vk_l: int
    vk_f: int
    vk_f5: int
    vk_add: int
    vk_subtract: int
    vk_0: int
    vk_return: int
    vk_prior: int
    vk_next: int
    vk_end: int
    vk_home: int
    vk_left: int
    vk_right: int
    sleep: Callable[[float], None] = time.sleep
    open_url: Callable[..., object] = webbrowser.open
    _ui: BrowserUiAutomation | None = field(default=None, init=False, repr=False)
    _controls: BrowserControls | None = field(default=None, init=False, repr=False)

    def normalize_text(self, text: str) -> str:
        return normalize_ui_text(text)

    def ui(self) -> BrowserUiAutomation:
        if self._ui is None:
            self._ui = BrowserUiAutomation(
                browser_names=self.browser_names,
                run_powershell=self.run_powershell,
                click=self.click,
            )
        return self._ui

    def controls(self) -> BrowserControls:
        if self._controls is None:
            self._controls = BrowserControls(
                activate_browser_window=self.activate_browser_window,
                shortcut=self.shortcut,
                tap=self.tap,
                click=self.click,
                get_browser_window_rect=self.get_browser_window_rect,
                click_first_browser_link=self.click_first_browser_link,
                click_browser_element_by_text=self.click_browser_element_by_text,
                type_text=self.type_text,
                open_url=self.open_url,
                keybd_event=self.keybd_event,
                mouse_event=self.mouse_event,
                keyup_flag=self.keyup_flag,
                mouse_wheel_flag=self.mouse_wheel_flag,
                vk_control=self.vk_control,
                vk_shift=self.vk_shift,
                vk_menu=self.vk_menu,
                vk_tab=self.vk_tab,
                vk_w=self.vk_w,
                vk_l=self.vk_l,
                vk_f=self.vk_f,
                vk_f5=self.vk_f5,
                vk_add=self.vk_add,
                vk_subtract=self.vk_subtract,
                vk_0=self.vk_0,
                vk_return=self.vk_return,
                vk_prior=self.vk_prior,
                vk_next=self.vk_next,
                vk_end=self.vk_end,
                vk_home=self.vk_home,
                vk_left=self.vk_left,
                vk_right=self.vk_right,
                sleep=self.sleep,
            )
        return self._controls

    def click_first_browser_link(self) -> bool:
        return self.ui().click_first_browser_link()

    def click_browser_element_by_text(self, query: str, app_names: Sequence[str] | None = None) -> bool:
        return self.ui().click_browser_element_by_text(query, app_names=app_names)

    def read_browser_elements(self, limit: int = 10):
        return self.ui().read_browser_elements(limit=limit)

    def new_tab(self) -> str:
        return self.controls().new_tab()

    def close_tab(self) -> str:
        return self.controls().close_tab()

    def next_tab(self) -> str:
        return self.controls().next_tab()

    def prev_tab(self) -> str:
        return self.controls().prev_tab()

    def back(self) -> str:
        return self.controls().back()

    def forward(self) -> str:
        return self.controls().forward()

    def refresh(self) -> str:
        return self.controls().refresh()

    def open_first_result(self) -> str:
        return self.controls().open_first_result()

    def open_focused_item(self) -> str:
        return self.controls().open_focused_item()

    def click_center(self) -> str:
        return self.controls().click_center()

    def click_text(self, query: str) -> str:
        return self.controls().click_text(query)

    def zoom_in(self) -> str:
        return self.controls().zoom_in()

    def zoom_out(self) -> str:
        return self.controls().zoom_out()

    def zoom_reset(self) -> str:
        return self.controls().zoom_reset()

    def search(self, query: str) -> str:
        return self.controls().search(query)

    def find(self, query: str) -> str:
        return self.controls().find(query)

    def scroll_down(self) -> str:
        return self.controls().scroll_down()

    def scroll_down_small(self) -> str:
        return self.controls().scroll_down_small()

    def scroll_up(self) -> str:
        return self.controls().scroll_up()

    def scroll_up_small(self) -> str:
        return self.controls().scroll_up_small()

    def scroll_top(self) -> str:
        return self.controls().scroll_top()

    def scroll_bottom(self) -> str:
        return self.controls().scroll_bottom()
