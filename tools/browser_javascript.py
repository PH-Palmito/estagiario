from __future__ import annotations

from collections.abc import Callable


def run_browser_javascript(
    script_body: str,
    *,
    activate_browser_window: Callable[[], bool],
    get_clipboard_text: Callable[[], str],
    set_clipboard_text: Callable[[str], None],
    shortcut: Callable[..., None],
    type_text: Callable[[str], None],
    tap: Callable[[int], None],
    sleep: Callable[[float], None],
    vk_control: int,
    vk_l: int,
    vk_v: int,
    vk_return: int,
) -> bool:
    if not activate_browser_window():
        return False

    old_clipboard = get_clipboard_text()

    try:
        shortcut(vk_control, vk_l)
        sleep(0.05)
        type_text("javascript:")
        set_clipboard_text(script_body)
        shortcut(vk_control, vk_v)
        sleep(0.05)
        tap(vk_return)
        sleep(0.25)
        return True
    except Exception:
        return False
    finally:
        set_clipboard_text(old_clipboard)


def run_browser_javascript_and_read_clipboard(
    script_body: str,
    marker: str,
    *,
    activate_browser_window: Callable[[], bool],
    get_clipboard_text: Callable[[], str],
    set_clipboard_text: Callable[[str], None],
    shortcut: Callable[..., None],
    type_text: Callable[[str], None],
    tap: Callable[[int], None],
    sleep: Callable[[float], None],
    vk_control: int,
    vk_l: int,
    vk_v: int,
    vk_return: int,
    timeout: float = 0.8,
) -> str:
    if not activate_browser_window():
        return ""

    old_clipboard = get_clipboard_text()

    try:
        set_clipboard_text("")
        shortcut(vk_control, vk_l)
        sleep(0.05)
        type_text("javascript:")
        set_clipboard_text(script_body)
        shortcut(vk_control, vk_v)
        sleep(0.05)
        tap(vk_return)
        sleep(timeout)
        copied = get_clipboard_text()

        if copied.startswith(marker):
            return copied[len(marker):].strip()

        return ""
    except Exception:
        return ""
    finally:
        set_clipboard_text(old_clipboard)
