from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import time


@dataclass(frozen=True)
class CachePolicy:
    name: str
    path: Path
    ttl_seconds: int
    requires_content_fingerprint: bool = False


BRIEFING_CACHE_POLICY = CachePolicy(
    name="daily_briefing",
    path=Path("memory/briefing_cache.json"),
    ttl_seconds=15 * 60,
)

INVESTMENT_SUMMARY_CACHE_POLICY = CachePolicy(
    name="investment_summary",
    path=Path("memory/investment_summary_cache.json"),
    ttl_seconds=10 * 60,
)

INVESTMENT_REPORT_CACHE_POLICY = CachePolicy(
    name="investment_report",
    path=Path("memory/investment_report_cache.json"),
    ttl_seconds=10 * 60,
)

VISION_SCREEN_CACHE_POLICY = CachePolicy(
    name="vision_screen",
    path=Path("memory/vision_screen_cache.json"),
    ttl_seconds=90,
    requires_content_fingerprint=True,
)

BROWSER_PRODUCT_CACHE_POLICY = CachePolicy(
    name="browser_products",
    path=Path("memory/browser_product_cache.json"),
    ttl_seconds=10 * 60,
)

KNOWN_CACHE_POLICIES = {
    policy.name: policy
    for policy in (
        BRIEFING_CACHE_POLICY,
        INVESTMENT_SUMMARY_CACHE_POLICY,
        INVESTMENT_REPORT_CACHE_POLICY,
        VISION_SCREEN_CACHE_POLICY,
        BROWSER_PRODUCT_CACHE_POLICY,
    )
}


def cache_policy_for(name: str) -> CachePolicy:
    key = str(name or "").strip()
    try:
        return KNOWN_CACHE_POLICIES[key]
    except KeyError as exc:
        raise ValueError(f"Politica de cache desconhecida: {key}") from exc


def is_cache_fresh(created_at: float | int | str | None, ttl_seconds: int, *, now: float | None = None) -> bool:
    if ttl_seconds <= 0:
        return False
    try:
        created = float(created_at or 0)
    except (TypeError, ValueError):
        return False
    if created <= 0:
        return False
    current = time() if now is None else float(now)
    return current - created <= int(ttl_seconds)
