import ctypes
import os
import random
import re
import subprocess
import time
import webbrowser
from urllib.parse import quote_plus, urlparse

from config import INVESTIDOR10_PRIVATE_WALLET_URL, INVESTIDOR10_WALLET_URL
from llm.ollama_client import ask_model
from memory.investment_snapshot import save_investment_snapshot
from memory.public_wallet_refresh import (
    format_public_wallet_refresh_result,
    parse_wallet_text_blob,
    refresh_wallet_snapshot_auto,
)
from tools import browser_state
from tools.browser_controls import BrowserControls
from tools.browser_dom_reader import (
    PRODUCT_CARDS_MARKER,
    build_product_cards_script,
    parse_product_cards_payload,
)
from tools.browser_launcher import open_url_in_wallet_browser as launcher_open_url_in_wallet_browser
from tools.browser_listed_items import (
    BrowserListedItemCommands,
    click_query_variants,
)
from tools.browser_music import BrowserMusic
from tools.browser_page_text import (
    selected_text_items as _selected_text_items,
)
from tools.browser_screen_capture import BrowserScreenCapture
from tools.browser_screen_commands import BrowserScreenCommands
from tools.browser_screen_narrative import (
    clean_browser_title as _clean_browser_title,
)
from tools.browser_selection_commands import (
    BrowserSelectionCommands,
    build_translation_prompt,
    clean_translation_output,
)
from tools.browser_text_reader import BrowserTextReader, compact_selected_text
from tools.browser_ui_automation import BrowserUiAutomation, normalize_ui_text
from tools.browser_wallet_commands import BrowserWalletCommands
from tools.spotify_ui_automation import SpotifyUiAutomation
from tools.system_tools import focus_app
from tools.windows_input import (
    click as windows_click,
)
from tools.windows_input import (
    shortcut as windows_shortcut,
)
from tools.windows_input import (
    tap as windows_tap,
)
from tools.windows_input import (
    tap_times as windows_tap_times,
)
from tools.windows_input import (
    type_text as windows_type_text,
)
from tools.windows_shell import (
    POWERSHELL_EXE,
)
from tools.windows_shell import (
    activate_window_names as windows_activate_window_names,
)
from tools.windows_shell import (
    get_clipboard_text as windows_get_clipboard_text,
)
from tools.windows_shell import (
    run_powershell as windows_run_powershell,
)
from tools.windows_shell import (
    set_clipboard_text as windows_set_clipboard_text,
)
from tools.windows_window import (
    app_window_rect as windows_app_window_rect,
)
from tools.windows_window import (
    first_window_rect as windows_first_window_rect,
)
from tools.windows_window import (
    foreground_window_capture_hash as windows_foreground_window_capture_hash,
)
from tools.windows_window import (
    foreground_window_rect as windows_foreground_window_rect,
)
from tools.windows_window import (
    foreground_window_title as windows_foreground_window_title,
)

user32 = ctypes.windll.user32
try:
    # Keeps UI Automation coordinates aligned with mouse coordinates on scaled/multi-monitor setups.
    user32.SetProcessDPIAware()
except Exception:
    pass

BROWSER_ACTIVATE_NAMES = ["chrome", "msedge", "firefox", "opera", "brave"]

VK_CONTROL = 0x11
VK_MENU = 0x12
VK_SHIFT = 0x10
VK_TAB = 0x09
VK_A = 0x41
VK_C = 0x43
VK_ESCAPE = 0x1B
VK_L = 0x4C
VK_V = 0x56
VK_W = 0x57
VK_F = 0x46
VK_R = 0x52
VK_F5 = 0x74
VK_ADD = 0x6B
VK_SUBTRACT = 0x6D
VK_0 = 0x30
VK_BACK = 0x08
VK_RETURN = 0x0D
VK_PRIOR = 0x21
VK_NEXT = 0x22
VK_END = 0x23
VK_HOME = 0x24
VK_SPACE = 0x20
VK_DOWN = 0x28
VK_UP = 0x26
VK_LEFT = 0x25
VK_RIGHT = 0x27

KEYEVENTF_KEYUP = 0x0002
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
DEFAULT_INVESTIDOR10_WALLET_URL = (
    INVESTIDOR10_WALLET_URL
    or INVESTIDOR10_PRIVATE_WALLET_URL
    or "https://investidor10.com.br/wallet/my-wallet"
)
_BROWSER_CONTROLS = None
_BROWSER_MUSIC = None
_BROWSER_TEXT_READER = None
_BROWSER_UI = None
_SPOTIFY_UI = None


def _clear_browser_snapshot(context: str = ""):
    browser_state.clear_browser_snapshot(context)


def _set_browser_elements(elements, context: str = ""):
    browser_state.set_browser_elements(elements, context)


def _remember_text_items(lines, context: str = ""):
    browser_state.remember_text_items(lines, context=context)


def _remember_browser_analysis(summary: str, lines=None, page_url: str = "", page_title: str = "", source: str = "pagina"):
    browser_state.remember_browser_analysis(summary, lines=lines, page_url=page_url, page_title=page_title, source=source)


def _get_foreground_window_title() -> str:
    return windows_foreground_window_title(user32)


def _get_foreground_window_rect():
    return windows_foreground_window_rect(user32)


def _get_foreground_window_capture_hash() -> str:
    return windows_foreground_window_capture_hash(
        get_rect_func=_get_foreground_window_rect,
        run_powershell_func=_run_powershell,
    )


def _browser_context_signature() -> str:
    title = _get_foreground_window_title()
    if not title:
        return ""

    title = re.sub(r"\s+", " ", title).strip()
    title_signature = _normalize_text_for_match(title)
    page_url = _get_browser_url()
    if page_url:
        parsed = urlparse(page_url)
        url_signature = _normalize_text_for_match(f"{parsed.netloc}{parsed.path}")
        if url_signature:
            title_signature = f"{title_signature}|{url_signature}"
    capture_hash = _get_foreground_window_capture_hash()
    if capture_hash:
        return f"{title_signature}|{capture_hash[:16]}"
    return title_signature


def _refresh_browser_context() -> str:
    context = _browser_context_signature()
    if browser_state.browser_context_changed(context):
        _clear_browser_snapshot(context=context)
    else:
        browser_state.mark_browser_context(context)

    return context


def _browser_context_recently_changed(window_seconds: float = 1.2) -> bool:
    return browser_state.browser_context_recently_changed(window_seconds)



def _run_powershell(script: str, timeout_seconds: int = 10) -> subprocess.CompletedProcess:
    return windows_run_powershell(script, timeout_seconds=timeout_seconds)


def _get_clipboard_text() -> str:
    return windows_get_clipboard_text(run_powershell_func=_run_powershell)


def _set_clipboard_text(text: str):
    windows_set_clipboard_text(text, powershell_exe=POWERSHELL_EXE)


def _activate_window_names(names) -> bool:
    return windows_activate_window_names(names, run_powershell_func=_run_powershell)


def _open_url_in_wallet_browser(url: str) -> str:
    return launcher_open_url_in_wallet_browser(url)


def _activate_browser_window() -> bool:
    return _activate_window_names(BROWSER_ACTIVATE_NAMES)


def _tap(vk_code: int):
    windows_tap(vk_code, keybd_event=user32.keybd_event, keyup_flag=KEYEVENTF_KEYUP, sleep=time.sleep)


def _tap_times(vk_code: int, times: int, delay: float = 0.08):
    windows_tap_times(
        vk_code,
        times,
        delay=delay,
        keybd_event=user32.keybd_event,
        keyup_flag=KEYEVENTF_KEYUP,
        sleep=time.sleep,
    )


def _click(x: int, y: int, clicks: int = 1):
    windows_click(
        x,
        y,
        clicks=clicks,
        set_cursor_pos=user32.SetCursorPos,
        mouse_event=user32.mouse_event,
        leftdown_flag=MOUSEEVENTF_LEFTDOWN,
        leftup_flag=MOUSEEVENTF_LEFTUP,
        sleep=time.sleep,
    )


def _get_app_window_rect(app_name: str):
    return windows_app_window_rect(app_name, run_powershell_func=_run_powershell)


def _get_browser_window_rect():
    return windows_first_window_rect(BROWSER_ACTIVATE_NAMES, get_app_window_rect_func=_get_app_window_rect)


def _browser_ui() -> BrowserUiAutomation:
    global _BROWSER_UI
    if _BROWSER_UI is None:
        _BROWSER_UI = BrowserUiAutomation(
            browser_names=BROWSER_ACTIVATE_NAMES,
            run_powershell=_run_powershell,
            click=_click,
        )
    return _BROWSER_UI


def _click_first_browser_link():
    return _browser_ui().click_first_browser_link()


def _normalize_text_for_match(text: str) -> str:
    return normalize_ui_text(text)


def _click_browser_item_from_text(text: str) -> bool:
    for query in click_query_variants(text):
        if _click_browser_element_by_text(query):
            return True

    return False


def _run_browser_javascript(script_body: str) -> bool:
    if not _activate_browser_window():
        return False

    old_clipboard = _get_clipboard_text()

    try:
        _shortcut(VK_CONTROL, VK_L)
        time.sleep(0.05)
        _type_text("javascript:")
        _set_clipboard_text(script_body)
        _shortcut(VK_CONTROL, VK_V)
        time.sleep(0.05)
        _tap(VK_RETURN)
        time.sleep(0.25)
        return True
    except Exception:
        return False
    finally:
        _set_clipboard_text(old_clipboard)


def _run_browser_javascript_and_read_clipboard(script_body: str, marker: str, timeout: float = 0.8) -> str:
    if not _activate_browser_window():
        return ""

    old_clipboard = _get_clipboard_text()

    try:
        _set_clipboard_text("")
        _shortcut(VK_CONTROL, VK_L)
        time.sleep(0.05)
        _type_text("javascript:")
        _set_clipboard_text(script_body)
        _shortcut(VK_CONTROL, VK_V)
        time.sleep(0.05)
        _tap(VK_RETURN)
        time.sleep(timeout)
        copied = _get_clipboard_text()

        if copied.startswith(marker):
            return copied[len(marker):].strip()

        return ""
    except Exception:
        return ""
    finally:
        _set_clipboard_text(old_clipboard)


def _click_page_item_by_text(text: str) -> bool:
    # Disabled: address-bar JavaScript bookmarklets can be interpreted as a search by Chrome.
    # Keep product clicks conservative until we have a safer browser-control channel.
    return False


def _click_browser_element_by_text(query: str, app_names=None):
    return _browser_ui().click_browser_element_by_text(query, app_names=app_names)


def _read_browser_elements(limit: int = 10):
    return _browser_ui().read_browser_elements(limit=limit)


def _screen_list_intro() -> str:
    return random.choice(
        [
            "Consegui ler texto da pagina",
            "Isto foi o que achei na pagina",
            "Encontrei estes pontos na tela",
            "O que estou vendo na pagina e",
        ]
    )


def _screen_summary_intro() -> str:
    return random.choice(
        [
            "Resumo da tela",
            "Panorama da tela",
            "Visao rapida da tela",
        ]
    )


def _browser_screen_capture() -> BrowserScreenCapture:
    return BrowserScreenCapture(
        activate_browser_window=_activate_browser_window,
        get_clipboard_text=_get_clipboard_text,
        set_clipboard_text=_set_clipboard_text,
        shortcut=_shortcut,
        tap=_tap,
        read_browser_elements=_read_browser_elements,
        browser_context_recently_changed=_browser_context_recently_changed,
        vk_control=VK_CONTROL,
        vk_a=VK_A,
        vk_c=VK_C,
        vk_escape=VK_ESCAPE,
        vk_l=VK_L,
    )


def _get_browser_url() -> str:
    return _browser_screen_capture().get_browser_url()


def _read_screen_content_lines(
    item_limit: int,
    page_limit: int,
    page_url: str,
    page_title: str,
):
    return _browser_screen_capture().read_screen_content_lines(
        item_limit=item_limit,
        page_limit=page_limit,
        page_url=page_url,
        page_title=page_title,
    )


def _read_product_cards_via_javascript(limit: int = 10):
    script = build_product_cards_script(limit=limit, marker=PRODUCT_CARDS_MARKER)
    copied = _run_browser_javascript_and_read_clipboard(script, PRODUCT_CARDS_MARKER)
    return parse_product_cards_payload(copied, limit=limit)


def _read_page_text_via_clipboard(limit: int = 10, page_url: str = "", page_title: str = ""):
    return _browser_screen_capture().read_page_text_via_clipboard(
        limit=limit,
        page_url=page_url,
        page_title=page_title,
    )


def _browser_screen_commands() -> BrowserScreenCommands:
    return BrowserScreenCommands(
        activate_browser_window=_activate_browser_window,
        refresh_browser_context=_refresh_browser_context,
        get_browser_url=_get_browser_url,
        get_page_title=lambda: _clean_browser_title(_get_foreground_window_title()),
        read_screen_content_lines=_read_screen_content_lines,
        clear_browser_snapshot=_clear_browser_snapshot,
        set_browser_elements=_set_browser_elements,
        remember_text_items=_remember_text_items,
        remember_browser_analysis=_remember_browser_analysis,
        screen_summary_intro=_screen_summary_intro,
        save_investment_snapshot=save_investment_snapshot,
    )


def _browser_wallet_commands() -> BrowserWalletCommands:
    return BrowserWalletCommands(
        private_wallet_url=INVESTIDOR10_PRIVATE_WALLET_URL,
        default_wallet_url=DEFAULT_INVESTIDOR10_WALLET_URL,
        configured_wallet_url=INVESTIDOR10_WALLET_URL,
        open_url_in_wallet_browser=_open_url_in_wallet_browser,
        read_full_page_text_from_foreground=_read_full_page_text_from_foreground,
        read_full_page_text_from_browser=_read_full_page_text_from_browser,
        click_browser_element_by_text=_click_browser_element_by_text,
        activate_window_names=_activate_window_names,
        shortcut=_shortcut,
        browser_close_tab=browser_close_tab,
        parse_wallet_text_blob=parse_wallet_text_blob,
        refresh_wallet_snapshot_auto=refresh_wallet_snapshot_auto,
        format_public_wallet_refresh_result=format_public_wallet_refresh_result,
        webbrowser_open=webbrowser.open,
        investment_snapshot=browser_investment_snapshot,
        vk_control=VK_CONTROL,
        vk_w=VK_W,
    )


def _browser_selection_commands() -> BrowserSelectionCommands:
    return BrowserSelectionCommands(
        read_selected_text_from_browser=_read_selected_text_from_browser,
        compact_selected_text=_compact_selected_text,
        clear_browser_snapshot=_clear_browser_snapshot,
        set_last_selected_text=browser_state.set_last_selected_text,
        last_selected_text=browser_state.last_selected_text,
        remember_browser_analysis=_remember_browser_analysis,
        remember_text_items=_remember_text_items,
        selected_text_items=_selected_text_items,
        ask_model=ask_model,
    )


def _browser_listed_item_commands() -> BrowserListedItemCommands:
    return BrowserListedItemCommands(
        activate_browser_window=_activate_browser_window,
        refresh_browser_context=_refresh_browser_context,
        listed_browser_elements=browser_state.listed_browser_elements,
        describe_screen=browser_describe_screen,
        click_page_item_by_text=_click_page_item_by_text,
        click_browser_item_from_text=_click_browser_item_from_text,
        browser_find=browser_find,
        click=_click,
        sleep=time.sleep,
    )


def _click_spotify_track_by_name(query: str):
    return _spotify_ui().click_track_by_name(query)


def _click_spotify_first_visible_track():
    return _spotify_ui().click_first_visible_track()


def spotify_diagnostic():
    return _spotify_ui().diagnostic()


def _shortcut(*vk_codes: int):
    windows_shortcut(*vk_codes, keybd_event=user32.keybd_event, keyup_flag=KEYEVENTF_KEYUP, sleep=time.sleep)


def _type_text(text: str):
    user32.VkKeyScanW.restype = ctypes.c_short
    windows_type_text(
        text,
        vk_key_scan=user32.VkKeyScanW,
        keybd_event=user32.keybd_event,
        tap_func=_tap,
        vk_shift=VK_SHIFT,
        keyup_flag=KEYEVENTF_KEYUP,
        sleep=time.sleep,
    )


def _browser_controls() -> BrowserControls:
    global _BROWSER_CONTROLS
    if _BROWSER_CONTROLS is None:
        _BROWSER_CONTROLS = BrowserControls(
            activate_browser_window=_activate_browser_window,
            shortcut=_shortcut,
            tap=_tap,
            click=_click,
            get_browser_window_rect=_get_browser_window_rect,
            click_first_browser_link=_click_first_browser_link,
            click_browser_element_by_text=_click_browser_element_by_text,
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
        )
    return _BROWSER_CONTROLS


def _spotify_ui() -> SpotifyUiAutomation:
    global _SPOTIFY_UI
    if _SPOTIFY_UI is None:
        _SPOTIFY_UI = SpotifyUiAutomation(
            run_powershell=_run_powershell,
            click=_click,
            set_cursor_pos=user32.SetCursorPos,
            sleep=time.sleep,
            focus_app=focus_app,
        )
    return _SPOTIFY_UI


def _browser_music() -> BrowserMusic:
    global _BROWSER_MUSIC
    if _BROWSER_MUSIC is None:
        _BROWSER_MUSIC = BrowserMusic(
            normalize_text=_normalize_text_for_match,
            os_startfile=os.startfile,
            sleep=time.sleep,
            focus_app=focus_app,
            open_url=webbrowser.open,
            click_track_by_name=_click_spotify_track_by_name,
            click_first_visible_track=_click_spotify_first_visible_track,
        )
    return _BROWSER_MUSIC


def _browser_text_reader() -> BrowserTextReader:
    global _BROWSER_TEXT_READER
    if _BROWSER_TEXT_READER is None:
        _BROWSER_TEXT_READER = BrowserTextReader(
            activate_browser_window=_activate_browser_window,
            activate_window_names=_activate_window_names,
            get_clipboard_text=_get_clipboard_text,
            set_clipboard_text=_set_clipboard_text,
            shortcut=_shortcut,
            tap=_tap,
            sleep=time.sleep,
            vk_control=VK_CONTROL,
            vk_c=VK_C,
            vk_a=VK_A,
            vk_escape=VK_ESCAPE,
        )
    return _BROWSER_TEXT_READER


def browser_new_tab():
    return _browser_controls().new_tab()


def browser_close_tab():
    return _browser_controls().close_tab()


def browser_next_tab():
    return _browser_controls().next_tab()


def browser_prev_tab():
    return _browser_controls().prev_tab()


def browser_back():
    return _browser_controls().back()


def browser_forward():
    return _browser_controls().forward()


def browser_refresh():
    return _browser_controls().refresh()


def browser_open_first_result():
    return _browser_controls().open_first_result()


def browser_open_focused_item():
    return _browser_controls().open_focused_item()


def browser_click_center():
    return _browser_controls().click_center()


def browser_click_text(query: str):
    return _browser_controls().click_text(query)


def browser_click_listed_item(index: int):
    return _browser_listed_item_commands().click_listed_item(index)


def browser_describe_listed_item(index: int):
    return _browser_listed_item_commands().describe_listed_item(index)


def _read_selected_text_from_browser(app_name: str | None = None):
    return _browser_text_reader().read_selected_text(app_name=app_name)


def _read_full_page_text_from_browser(wait_seconds: float = 0.35, app_name: str | None = None):
    return _browser_text_reader().read_full_page_text_from_browser(wait_seconds=wait_seconds, app_name=app_name)


def _read_full_page_text_from_foreground(wait_seconds: float = 0.35):
    return _browser_text_reader().read_full_page_text_from_foreground(wait_seconds=wait_seconds)


def _compact_selected_text(text: str, max_length: int = 650):
    return compact_selected_text(text, max_length=max_length)


def browser_read_selection():
    return _browser_selection_commands().read_selection()


def _translate_with_ollama(text: str, target_language: str = "portugues do Brasil"):
    prompt = build_translation_prompt(text, target_language=target_language)
    return ask_model(
        prompt,
        timeout_seconds=20,
        num_predict=500,
        temperature=0.1,
    ).strip()


def _clean_translation_output(text: str):
    return clean_translation_output(text)


def browser_translate_selection():
    return _browser_selection_commands().translate_selection()


def browser_translate_last_selection():
    return _browser_selection_commands().translate_last_selection()


def browser_read_selected_products():
    return _browser_selection_commands().read_selected_products()


def browser_cheapest_listed_item():
    return _browser_listed_item_commands().cheapest_listed_item()


def browser_summarize_screen():
    return _browser_screen_commands().summarize_screen()


def browser_explain_screen():
    return _browser_screen_commands().explain_screen()


def browser_investment_snapshot():
    return _browser_screen_commands().investment_snapshot()


def _visible_wallet_capture_summary_legacy(url: str, close_tab: bool = True):
    return _browser_wallet_commands().visible_capture_summary_legacy(url, close_tab=close_tab)


def _visible_wallet_capture_summary(url: str, close_tab: bool = True, max_seconds: float = 12.0):
    return _browser_wallet_commands().visible_capture_summary(
        url,
        close_tab=close_tab,
        max_seconds=max_seconds,
    )


def browser_open_wallet_and_summarize():
    return _browser_wallet_commands().open_wallet_and_summarize()


def browser_describe_screen():
    return _browser_screen_commands().describe_screen()


def browser_read_more():
    if not _activate_browser_window():
        return "Nao encontrei um navegador aberto para ler mais."

    user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, -550, 0)
    time.sleep(0.25)
    result = browser_describe_screen()

    if result.startswith("Vejo na tela:"):
        return result.replace("Vejo na tela:", "Mais abaixo vejo:", 1)

    if result.startswith("Consegui ler texto da pagina:"):
        return result.replace("Consegui ler texto da pagina:", "Mais abaixo consegui ler:", 1)

    return result


def browser_zoom_in():
    return _browser_controls().zoom_in()


def browser_zoom_out():
    return _browser_controls().zoom_out()


def browser_zoom_reset():
    return _browser_controls().zoom_reset()


def browser_search(query: str):
    return _browser_controls().search(query)


def browser_find(query: str):
    return _browser_controls().find(query)


def browser_scroll_down():
    return _browser_controls().scroll_down()


def browser_scroll_down_small():
    return _browser_controls().scroll_down_small()


def browser_scroll_up():
    return _browser_controls().scroll_up()


def browser_scroll_up_small():
    return _browser_controls().scroll_up_small()


def browser_scroll_top():
    return _browser_controls().scroll_top()


def browser_scroll_bottom():
    return _browser_controls().scroll_bottom()


def browser_search_site(site: str, query: str):
    if not site or not query:
        return "Qual site e qual pesquisa?"

    site = site.strip()
    query = query.strip()

    if "mercadolivre.com.br" in site:
        webbrowser.open(f"https://lista.mercadolivre.com.br/{quote_plus(query)}", new=2)
        return f"Pesquisando {query} no Mercado Livre em uma nova aba."

    if "magazineluiza.com.br" in site:
        webbrowser.open(f"https://www.magazineluiza.com.br/busca/{quote_plus(query)}/", new=2)
        return f"Pesquisando {query} no Magazine Luiza em uma nova aba."

    if "youtube.com" in site:
        webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}", new=2)
        return f"Pesquisando {query} no YouTube em uma nova aba."

    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query + ' site:' + site)}", new=2)
    return f"Pesquisando {query} em {site} em uma nova aba."


def browser_search_music(service: str, query: str):
    return _browser_music().search_music(service, query)


def browser_surprise_music(service: str = "spotify"):
    return _browser_music().surprise_music(service)


def browser_music_session(service: str = "spotify", vibe: str = ""):
    return _browser_music().music_session(service, vibe)


def browser_queue_music(service: str, query: str):
    return _browser_music().queue_music(service, query)


def spotify_like_current_track():
    return _browser_music().like_current_track()


def spotify_dislike_current_track():
    return _browser_music().dislike_current_track()


def spotify_more_like_current_track():
    return _browser_music().more_like_current_track()


def spotify_less_music_vibe(vibe: str = ""):
    return _browser_music().less_music_vibe(vibe)




