import subprocess
import time
import webbrowser

from llm.ollama_client import ask_model
from memory.investment_snapshot import save_investment_snapshot
from tools import browser_state
from tools.browser_control_runtime import BrowserControlRuntime
from tools.browser_context import (
    browser_context_signature,
    refresh_browser_context,
)
from tools.browser_launcher import open_url_in_wallet_browser as launcher_open_url_in_wallet_browser
from tools.browser_javascript_runtime import BrowserJavascriptRuntime
from tools.browser_listed_item_runtime import BrowserListedItemRuntime
from tools.browser_music_runtime import BrowserMusicRuntime
from tools.browser_page_text import (
    selected_text_items as _selected_text_items,
)
from tools.browser_read_more import browser_read_more as browser_read_more_command
from tools.browser_screen_narrative import (
    clean_browser_title as _clean_browser_title,
)
from tools.browser_screen_runtime import BrowserScreenRuntime
from tools.browser_site_search import browser_search_site as browser_search_site_command
from tools.browser_text_runtime import BrowserTextRuntime
from tools.browser_wallet_runtime import BrowserWalletRuntime
from tools.browser_windows_io import BrowserWindowsIO
from tools.browser_windows_context import (
    BROWSER_ACTIVATE_NAMES,
    KEYEVENTF_KEYUP,
    MOUSEEVENTF_WHEEL,
    VK_0,
    VK_A,
    VK_ADD,
    VK_C,
    VK_CONTROL,
    VK_END,
    VK_ESCAPE,
    VK_F,
    VK_F5,
    VK_HOME,
    VK_L,
    VK_LEFT,
    VK_MENU,
    VK_NEXT,
    VK_PRIOR,
    VK_RETURN,
    VK_RIGHT,
    VK_SHIFT,
    VK_SUBTRACT,
    VK_TAB,
    VK_V,
    VK_W,
    browser_windows_io,
    user32,
)

_BROWSER_MUSIC_RUNTIME = None
_BROWSER_SCREEN_RUNTIME = None
_BROWSER_TEXT_RUNTIME = None
_BROWSER_CONTROL_RUNTIME = None
_BROWSER_WALLET_RUNTIME = None
_BROWSER_LISTED_ITEM_RUNTIME = None
_BROWSER_JAVASCRIPT_RUNTIME = None


def _browser_windows_io() -> BrowserWindowsIO:
    return browser_windows_io()


def _clear_browser_snapshot(context: str = ""):
    browser_state.clear_browser_snapshot(context)


def _set_browser_elements(elements, context: str = ""):
    browser_state.set_browser_elements(elements, context)


def _remember_text_items(lines, context: str = ""):
    browser_state.remember_text_items(lines, context=context)


def _remember_browser_analysis(summary: str, lines=None, page_url: str = "", page_title: str = "", source: str = "pagina"):
    browser_state.remember_browser_analysis(summary, lines=lines, page_url=page_url, page_title=page_title, source=source)


def _get_foreground_window_title() -> str:
    return _browser_windows_io().foreground_window_title()


def _get_foreground_window_rect():
    return _browser_windows_io().foreground_window_rect()


def _get_foreground_window_capture_hash() -> str:
    return _browser_windows_io().foreground_window_capture_hash()


def _browser_context_signature() -> str:
    return browser_context_signature(
        get_title=_get_foreground_window_title,
        get_url=_get_browser_url,
        get_capture_hash=_get_foreground_window_capture_hash,
        normalize_text=_normalize_text_for_match,
    )


def _refresh_browser_context() -> str:
    return refresh_browser_context(
        get_signature=_browser_context_signature,
        clear_snapshot=_clear_browser_snapshot,
        context_changed=browser_state.browser_context_changed,
        mark_context=browser_state.mark_browser_context,
    )


def _browser_context_recently_changed(window_seconds: float = 1.2) -> bool:
    return browser_state.browser_context_recently_changed(window_seconds)



def _run_powershell(script: str, timeout_seconds: int = 10) -> subprocess.CompletedProcess:
    return _browser_windows_io().run_powershell(script, timeout_seconds=timeout_seconds)


def _get_clipboard_text() -> str:
    return _browser_windows_io().get_clipboard_text()


def _set_clipboard_text(text: str):
    _browser_windows_io().set_clipboard_text(text)


def _activate_window_names(names) -> bool:
    return _browser_windows_io().activate_window_names(names)


def _open_url_in_wallet_browser(url: str) -> str:
    return launcher_open_url_in_wallet_browser(url)


def _activate_browser_window() -> bool:
    return _browser_windows_io().activate_browser_window()


def _tap(vk_code: int):
    _browser_windows_io().tap(vk_code)


def _tap_times(vk_code: int, times: int, delay: float = 0.08):
    _browser_windows_io().tap_times(vk_code, times, delay=delay)


def _click(x: int, y: int, clicks: int = 1):
    _browser_windows_io().click(x, y, clicks=clicks)


def _get_app_window_rect(app_name: str):
    return _browser_windows_io().app_window_rect(app_name)


def _get_browser_window_rect():
    return _browser_windows_io().browser_window_rect()


def _browser_control_runtime() -> BrowserControlRuntime:
    global _BROWSER_CONTROL_RUNTIME
    if _BROWSER_CONTROL_RUNTIME is None:
        _BROWSER_CONTROL_RUNTIME = BrowserControlRuntime(
            browser_names=BROWSER_ACTIVATE_NAMES,
            activate_browser_window=_activate_browser_window,
            run_powershell=_run_powershell,
            shortcut=_shortcut,
            tap=_tap,
            click=_click,
            get_browser_window_rect=_get_browser_window_rect,
            type_text=_type_text,
            open_url=webbrowser.open,
            keybd_event=user32.keybd_event,
            mouse_event=user32.mouse_event,
            keyup_flag=KEYEVENTF_KEYUP,
            mouse_wheel_flag=MOUSEEVENTF_WHEEL,
            vk_control=VK_CONTROL,
            vk_shift=VK_SHIFT,
            vk_menu=VK_MENU,
            vk_tab=VK_TAB,
            vk_w=VK_W,
            vk_l=VK_L,
            vk_f=VK_F,
            vk_f5=VK_F5,
            vk_add=VK_ADD,
            vk_subtract=VK_SUBTRACT,
            vk_0=VK_0,
            vk_return=VK_RETURN,
            vk_prior=VK_PRIOR,
            vk_next=VK_NEXT,
            vk_end=VK_END,
            vk_home=VK_HOME,
            vk_left=VK_LEFT,
            vk_right=VK_RIGHT,
            sleep=time.sleep,
        )
    return _BROWSER_CONTROL_RUNTIME


def _click_first_browser_link():
    return _browser_control_runtime().click_first_browser_link()


def _normalize_text_for_match(text: str) -> str:
    return _browser_control_runtime().normalize_text(text)


def _run_browser_javascript(script_body: str) -> bool:
    return _browser_javascript_runtime().run_javascript(script_body)


def _run_browser_javascript_and_read_clipboard(script_body: str, marker: str, timeout: float = 0.8) -> str:
    return _browser_javascript_runtime().run_javascript_and_read_clipboard(script_body, marker, timeout=timeout)


def _click_page_item_by_text(text: str) -> bool:
    # Disabled: address-bar JavaScript bookmarklets can be interpreted as a search by Chrome.
    # Keep product clicks conservative until we have a safer browser-control channel.
    return False


def _click_browser_element_by_text(query: str, app_names=None):
    return _browser_control_runtime().click_browser_element_by_text(query, app_names=app_names)


def _read_browser_elements(limit: int = 10):
    return _browser_control_runtime().read_browser_elements(limit=limit)


def _browser_javascript_runtime() -> BrowserJavascriptRuntime:
    global _BROWSER_JAVASCRIPT_RUNTIME
    if _BROWSER_JAVASCRIPT_RUNTIME is None:
        _BROWSER_JAVASCRIPT_RUNTIME = BrowserJavascriptRuntime(
            activate_browser_window=_activate_browser_window,
            get_clipboard_text=_get_clipboard_text,
            set_clipboard_text=_set_clipboard_text,
            shortcut=_shortcut,
            type_text=_type_text,
            tap=_tap,
            sleep=time.sleep,
            vk_control=VK_CONTROL,
            vk_l=VK_L,
            vk_v=VK_V,
            vk_return=VK_RETURN,
        )
    return _BROWSER_JAVASCRIPT_RUNTIME


def _browser_screen_runtime() -> BrowserScreenRuntime:
    global _BROWSER_SCREEN_RUNTIME
    if _BROWSER_SCREEN_RUNTIME is None:
        _BROWSER_SCREEN_RUNTIME = BrowserScreenRuntime(
            activate_browser_window=_activate_browser_window,
            refresh_browser_context=_refresh_browser_context,
            get_clipboard_text=_get_clipboard_text,
            set_clipboard_text=_set_clipboard_text,
            shortcut=_shortcut,
            tap=_tap,
            read_browser_elements=_read_browser_elements,
            browser_context_recently_changed=_browser_context_recently_changed,
            get_foreground_window_title=_get_foreground_window_title,
            clean_browser_title=_clean_browser_title,
            clear_browser_snapshot=_clear_browser_snapshot,
            set_browser_elements=_set_browser_elements,
            remember_text_items=_remember_text_items,
            remember_browser_analysis=_remember_browser_analysis,
            save_investment_snapshot=save_investment_snapshot,
            vk_control=VK_CONTROL,
            vk_a=VK_A,
            vk_c=VK_C,
            vk_escape=VK_ESCAPE,
            vk_l=VK_L,
            sleep=time.sleep,
        )
    return _BROWSER_SCREEN_RUNTIME


def _get_browser_url() -> str:
    return _browser_screen_runtime().get_browser_url()


def _read_screen_content_lines(
    item_limit: int,
    page_limit: int,
    page_url: str,
    page_title: str,
):
    return _browser_screen_runtime().read_screen_content_lines(
        item_limit=item_limit,
        page_limit=page_limit,
        page_url=page_url,
        page_title=page_title,
    )


def _read_product_cards_via_javascript(limit: int = 10):
    return _browser_javascript_runtime().read_product_cards(limit=limit)


def _read_page_text_via_clipboard(limit: int = 10, page_url: str = "", page_title: str = ""):
    return _browser_screen_runtime().read_page_text_via_clipboard(
        limit=limit,
        page_url=page_url,
        page_title=page_title,
    )


def _browser_wallet_runtime() -> BrowserWalletRuntime:
    global _BROWSER_WALLET_RUNTIME
    if _BROWSER_WALLET_RUNTIME is None:
        _BROWSER_WALLET_RUNTIME = BrowserWalletRuntime(
            open_url_in_wallet_browser=_open_url_in_wallet_browser,
            read_full_page_text_from_foreground=_read_full_page_text_from_foreground,
            read_full_page_text_from_browser=_read_full_page_text_from_browser,
            click_browser_element_by_text=_click_browser_element_by_text,
            activate_window_names=_activate_window_names,
            shortcut=_shortcut,
            browser_close_tab=browser_close_tab,
            investment_snapshot=browser_investment_snapshot,
            vk_control=VK_CONTROL,
            vk_w=VK_W,
        )
    return _BROWSER_WALLET_RUNTIME


def _browser_listed_item_runtime() -> BrowserListedItemRuntime:
    global _BROWSER_LISTED_ITEM_RUNTIME
    if _BROWSER_LISTED_ITEM_RUNTIME is None:
        _BROWSER_LISTED_ITEM_RUNTIME = BrowserListedItemRuntime(
            activate_browser_window=_activate_browser_window,
            refresh_browser_context=_refresh_browser_context,
            listed_browser_elements=browser_state.listed_browser_elements,
            describe_screen=browser_describe_screen,
            click_page_item_by_text=_click_page_item_by_text,
            click_browser_element_by_text=_click_browser_element_by_text,
            browser_find=browser_find,
            click=_click,
            sleep=time.sleep,
        )
    return _BROWSER_LISTED_ITEM_RUNTIME


def _click_spotify_track_by_name(query: str):
    return _browser_music_runtime().spotify_ui().click_track_by_name(query)


def _click_spotify_first_visible_track():
    return _browser_music_runtime().spotify_ui().click_first_visible_track()


def spotify_diagnostic():
    return _browser_music_runtime().spotify_diagnostic()


def _shortcut(*vk_codes: int):
    _browser_windows_io().shortcut(*vk_codes)


def _type_text(text: str):
    _browser_windows_io().type_text(text, vk_shift=VK_SHIFT)


def _browser_music_runtime() -> BrowserMusicRuntime:
    global _BROWSER_MUSIC_RUNTIME
    if _BROWSER_MUSIC_RUNTIME is None:
        _BROWSER_MUSIC_RUNTIME = BrowserMusicRuntime(
            normalize_text=_normalize_text_for_match,
            run_powershell=_run_powershell,
            click=_click,
            set_cursor_pos=user32.SetCursorPos,
            sleep=time.sleep,
            open_url=webbrowser.open,
        )
    return _BROWSER_MUSIC_RUNTIME


def _browser_text_runtime() -> BrowserTextRuntime:
    global _BROWSER_TEXT_RUNTIME
    if _BROWSER_TEXT_RUNTIME is None:
        _BROWSER_TEXT_RUNTIME = BrowserTextRuntime(
            activate_browser_window=_activate_browser_window,
            activate_window_names=_activate_window_names,
            get_clipboard_text=_get_clipboard_text,
            set_clipboard_text=_set_clipboard_text,
            shortcut=_shortcut,
            tap=_tap,
            sleep=time.sleep,
            clear_browser_snapshot=_clear_browser_snapshot,
            set_last_selected_text=browser_state.set_last_selected_text,
            last_selected_text=browser_state.last_selected_text,
            remember_browser_analysis=_remember_browser_analysis,
            remember_text_items=_remember_text_items,
            selected_text_items=_selected_text_items,
            ask_model=ask_model,
            vk_control=VK_CONTROL,
            vk_c=VK_C,
            vk_a=VK_A,
            vk_escape=VK_ESCAPE,
        )
    return _BROWSER_TEXT_RUNTIME


def browser_new_tab():
    return _browser_control_runtime().new_tab()


def browser_close_tab():
    return _browser_control_runtime().close_tab()


def browser_next_tab():
    return _browser_control_runtime().next_tab()


def browser_prev_tab():
    return _browser_control_runtime().prev_tab()


def browser_back():
    return _browser_control_runtime().back()


def browser_forward():
    return _browser_control_runtime().forward()


def browser_refresh():
    return _browser_control_runtime().refresh()


def browser_open_first_result():
    return _browser_control_runtime().open_first_result()


def browser_open_focused_item():
    return _browser_control_runtime().open_focused_item()


def browser_click_center():
    return _browser_control_runtime().click_center()


def browser_click_text(query: str):
    return _browser_control_runtime().click_text(query)


def browser_click_listed_item(index: int):
    return _browser_listed_item_runtime().click_listed_item(index)


def browser_describe_listed_item(index: int):
    return _browser_listed_item_runtime().describe_listed_item(index)


def _read_selected_text_from_browser(app_name: str | None = None):
    return _browser_text_runtime().read_selected_text(app_name=app_name)


def _read_full_page_text_from_browser(wait_seconds: float = 0.35, app_name: str | None = None):
    return _browser_text_runtime().read_full_page_text_from_browser(wait_seconds=wait_seconds, app_name=app_name)


def _read_full_page_text_from_foreground(wait_seconds: float = 0.35):
    return _browser_text_runtime().read_full_page_text_from_foreground(wait_seconds=wait_seconds)


def _compact_selected_text(text: str, max_length: int = 650):
    return _browser_text_runtime().compact_selected_text(text, max_length=max_length)


def browser_read_selection():
    return _browser_text_runtime().read_selection()


def browser_translate_selection():
    return _browser_text_runtime().translate_selection()


def browser_translate_last_selection():
    return _browser_text_runtime().translate_last_selection()


def browser_read_selected_products():
    return _browser_text_runtime().read_selected_products()


def browser_cheapest_listed_item():
    return _browser_listed_item_runtime().cheapest_listed_item()


def browser_summarize_screen():
    return _browser_screen_runtime().summarize_screen()


def browser_explain_screen():
    return _browser_screen_runtime().explain_screen()


def browser_investment_snapshot():
    return _browser_screen_runtime().investment_snapshot()


def _visible_wallet_capture_summary_legacy(url: str, close_tab: bool = True):
    return _browser_wallet_runtime().visible_capture_summary_legacy(url, close_tab=close_tab)


def _visible_wallet_capture_summary(url: str, close_tab: bool = True, max_seconds: float = 12.0):
    return _browser_wallet_runtime().visible_capture_summary(
        url,
        close_tab=close_tab,
        max_seconds=max_seconds,
    )


def browser_open_wallet_and_summarize():
    return _browser_wallet_runtime().open_wallet_and_summarize()


def browser_describe_screen():
    return _browser_screen_runtime().describe_screen()


def browser_read_more():
    return browser_read_more_command(
        activate_browser_window=_activate_browser_window,
        mouse_wheel=lambda delta: user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, delta, 0),
        describe_screen=browser_describe_screen,
        sleep=time.sleep,
    )


def browser_zoom_in():
    return _browser_control_runtime().zoom_in()


def browser_zoom_out():
    return _browser_control_runtime().zoom_out()


def browser_zoom_reset():
    return _browser_control_runtime().zoom_reset()


def browser_search(query: str):
    return _browser_control_runtime().search(query)


def browser_find(query: str):
    return _browser_control_runtime().find(query)


def browser_scroll_down():
    return _browser_control_runtime().scroll_down()


def browser_scroll_down_small():
    return _browser_control_runtime().scroll_down_small()


def browser_scroll_up():
    return _browser_control_runtime().scroll_up()


def browser_scroll_up_small():
    return _browser_control_runtime().scroll_up_small()


def browser_scroll_top():
    return _browser_control_runtime().scroll_top()


def browser_scroll_bottom():
    return _browser_control_runtime().scroll_bottom()


def browser_search_site(site: str, query: str):
    return browser_search_site_command(site, query, open_url=webbrowser.open)


def browser_search_music(service: str, query: str):
    return _browser_music_runtime().search_music(service, query)


def browser_surprise_music(service: str = "spotify"):
    return _browser_music_runtime().surprise_music(service)


def browser_music_session(service: str = "spotify", vibe: str = ""):
    return _browser_music_runtime().music_session(service, vibe)


def browser_queue_music(service: str, query: str):
    return _browser_music_runtime().queue_music(service, query)


def spotify_like_current_track():
    return _browser_music_runtime().like_current_track()


def spotify_dislike_current_track():
    return _browser_music_runtime().dislike_current_track()


def spotify_more_like_current_track():
    return _browser_music_runtime().more_like_current_track()


def spotify_less_music_vibe(vibe: str = ""):
    return _browser_music_runtime().less_music_vibe(vibe)




