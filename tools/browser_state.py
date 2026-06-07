from __future__ import annotations

import re
import time

from memory.browser_product_cache import save_product_snapshot
from memory.vision_history import remember_vision_analysis

LAST_BROWSER_ELEMENTS = []
LAST_BROWSER_CONTEXT = ""
LAST_BROWSER_CONTEXT_CHANGED_AT = 0.0
LAST_SELECTED_TEXT = ""


def clear_browser_snapshot(context: str = ""):
    global LAST_BROWSER_ELEMENTS, LAST_BROWSER_CONTEXT, LAST_BROWSER_CONTEXT_CHANGED_AT

    LAST_BROWSER_ELEMENTS = []
    LAST_BROWSER_CONTEXT = context
    LAST_BROWSER_CONTEXT_CHANGED_AT = time.monotonic()


def set_browser_elements(elements, context: str = ""):
    global LAST_BROWSER_ELEMENTS, LAST_BROWSER_CONTEXT

    LAST_BROWSER_ELEMENTS = list(elements)
    LAST_BROWSER_CONTEXT = context
    try:
        save_product_snapshot(LAST_BROWSER_ELEMENTS, context=context)
    except Exception:
        pass


def remember_text_items(lines, context: str = ""):
    elements = [
        {
            "text": line,
            "x": None,
            "y": None,
            "type": "Text",
        }
        for line in lines
    ]
    set_browser_elements(elements, context=context)


def remember_browser_analysis(summary: str, lines=None, page_url: str = "", page_title: str = "", source: str = "pagina"):
    summary = re.sub(r"\s+", " ", str(summary or "")).strip()
    if not summary:
        return

    compact_lines = []
    for line in list(lines or [])[:30]:
        clean = re.sub(r"\s+", " ", str(line or "")).strip()
        if clean:
            compact_lines.append(clean)

    remember_vision_analysis(
        source,
        summary,
        details={
            "kind": "browser",
            "page_url": page_url or "",
            "page_title": page_title or "",
            "lines": compact_lines,
        },
    )


def browser_context_changed(context: str) -> bool:
    return bool(context and LAST_BROWSER_CONTEXT and context != LAST_BROWSER_CONTEXT)


def mark_browser_context(context: str) -> None:
    global LAST_BROWSER_CONTEXT, LAST_BROWSER_CONTEXT_CHANGED_AT

    if context and not LAST_BROWSER_CONTEXT:
        LAST_BROWSER_CONTEXT = context
        LAST_BROWSER_CONTEXT_CHANGED_AT = time.monotonic()


def browser_context_recently_changed(window_seconds: float = 1.2) -> bool:
    if LAST_BROWSER_CONTEXT_CHANGED_AT <= 0:
        return False
    return (time.monotonic() - LAST_BROWSER_CONTEXT_CHANGED_AT) <= window_seconds


def listed_browser_elements():
    return LAST_BROWSER_ELEMENTS


def set_last_selected_text(text: str) -> None:
    global LAST_SELECTED_TEXT
    LAST_SELECTED_TEXT = text


def last_selected_text() -> str:
    return LAST_SELECTED_TEXT
