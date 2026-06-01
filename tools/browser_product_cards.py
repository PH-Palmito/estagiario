from __future__ import annotations

from collections.abc import Callable

from tools.browser_dom_reader import (
    PRODUCT_CARDS_MARKER,
    build_product_cards_script,
    parse_product_cards_payload,
)


def read_product_cards_via_javascript(
    *,
    run_javascript_and_read_clipboard: Callable[[str, str], str],
    limit: int = 10,
    marker: str = PRODUCT_CARDS_MARKER,
) -> list[dict]:
    script = build_product_cards_script(limit=limit, marker=marker)
    copied = run_javascript_and_read_clipboard(script, marker)
    return parse_product_cards_payload(copied, limit=limit)
