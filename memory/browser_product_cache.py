from __future__ import annotations

import re
import time
from pathlib import Path

from core.cache_policy import BROWSER_PRODUCT_CACHE_POLICY, is_cache_fresh
from memory.json_store import read_json_file, write_json_atomic


PRODUCT_CACHE_PATH = BROWSER_PRODUCT_CACHE_POLICY.path


def _extract_brl_price(text: str) -> float | None:
    matches = re.findall(r"R\$\s*([\d\.]+,\d{2})", str(text or ""), flags=re.I)
    values = []
    for match in matches:
        try:
            values.append(float(match.replace(".", "").replace(",", ".")))
        except ValueError:
            continue
    return min(values) if values else None


def _clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "")).strip()


def _looks_like_product(text: str) -> bool:
    clean = _clean_text(text)
    if len(clean) < 8:
        return False
    if _extract_brl_price(clean) is not None:
        return True
    return bool(re.search(r"\b(celular|smartphone|notebook|iphone|galaxy|xiaomi|redmi|samsung|motorola|tablet)\b", clean, flags=re.I))


def _load_cache(path: Path | None = None) -> dict:
    return read_json_file(path or PRODUCT_CACHE_PATH, {}, validator=lambda value: isinstance(value, dict))


def save_product_snapshot(elements: list, *, context: str = "", source: str = "browser") -> dict:
    items = []
    seen = set()
    for element in list(elements or [])[:40]:
        if not isinstance(element, dict):
            continue
        text = _clean_text(str(element.get("text") or ""))
        if not _looks_like_product(text):
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        price = _extract_brl_price(text)
        items.append(
            {
                "text": text,
                "price": price,
                "x": element.get("x"),
                "y": element.get("y"),
                "type": str(element.get("type") or ""),
                "source": str(element.get("source") or source),
            }
        )
        if len(items) >= 20:
            break

    if not items:
        return _load_cache()

    payload = {
        "created_at": time.time(),
        "source": source,
        "context": _clean_text(context)[:300],
        "items": items,
    }
    write_json_atomic(PRODUCT_CACHE_PATH, payload, indent=2)
    return payload


def load_product_snapshot(*, max_age_seconds: int | None = None) -> dict:
    payload = _load_cache()
    ttl = BROWSER_PRODUCT_CACHE_POLICY.ttl_seconds if max_age_seconds is None else int(max_age_seconds)
    if not payload or not is_cache_fresh(payload.get("created_at"), ttl):
        return {}
    items = payload.get("items")
    if not isinstance(items, list) or not items:
        return {}
    return payload


def cached_product_items(*, max_age_seconds: int | None = None) -> list[dict]:
    snapshot = load_product_snapshot(max_age_seconds=max_age_seconds)
    items = snapshot.get("items") if isinstance(snapshot, dict) else []
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def format_cached_products(limit: int = 6) -> str:
    items = cached_product_items()
    if not items:
        return "Ainda nao tenho produtos recentes em cache."
    rows = [f"{index}. {_clean_text(item.get('text', ''))}" for index, item in enumerate(items[:limit], start=1)]
    return "Produtos recentes em cache: " + " ; ".join(rows) + "."


def describe_cached_product(index: int) -> str:
    items = cached_product_items()
    if index < 1:
        return "Qual item?"
    if index > len(items):
        return "Ainda nao tenho esse item no cache de produtos recente."
    return f"Item {index} em cache: {_clean_text(items[index - 1].get('text', ''))}."


def cheapest_cached_product() -> str:
    items = cached_product_items()
    priced = [
        (float(item.get("price")), index, _clean_text(item.get("text", "")))
        for index, item in enumerate(items, start=1)
        if isinstance(item.get("price"), (int, float)) and float(item.get("price")) > 0
    ]
    if not priced:
        return "Ainda nao tenho precos claros no cache de produtos recente."
    _price, index, text = min(priced, key=lambda entry: entry[0])
    return f"O mais barato no cache recente e o item {index}: {text}."
