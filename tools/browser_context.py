from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlparse

from tools import browser_state


def browser_context_signature(
    *,
    get_title: Callable[[], str],
    get_url: Callable[[], str],
    get_capture_hash: Callable[[], str],
    normalize_text: Callable[[str], str],
) -> str:
    title = get_title()
    if not title:
        return ""

    title = re.sub(r"\s+", " ", title).strip()
    title_signature = normalize_text(title)
    page_url = get_url()
    if page_url:
        parsed = urlparse(page_url)
        url_signature = normalize_text(f"{parsed.netloc}{parsed.path}")
        if url_signature:
            title_signature = f"{title_signature}|{url_signature}"

    capture_hash = get_capture_hash()
    if capture_hash:
        return f"{title_signature}|{capture_hash[:16]}"
    return title_signature


def refresh_browser_context(
    *,
    get_signature: Callable[[], str],
    clear_snapshot: Callable[..., None] = browser_state.clear_browser_snapshot,
    context_changed: Callable[[str], bool] = browser_state.browser_context_changed,
    mark_context: Callable[[str], None] = browser_state.mark_browser_context,
) -> str:
    context = get_signature()
    if context_changed(context):
        clear_snapshot(context=context)
    else:
        mark_context(context)

    return context
