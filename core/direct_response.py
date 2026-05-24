from __future__ import annotations

import difflib
import re

from core.router_utils import normalize_text

APP_CHOICE_ALIASES = {
    "app",
    "aplicativo",
    "programa",
    "exe",
    "eapp",
    "ehapp",
    "ap",
    "ape",
    "epe",
    "ep",
    "apepe",
}

SITE_CHOICE_ALIASES = {
    "site",
    "saite",
    "sait",
    "web",
    "pagina",
    "page",
    "navegador",
    "esite",
    "ehsite",
}


def is_confirmation_yes(text: str) -> bool:
    return normalize_text(text) in {"sim", "s", "confirmar", "ok", "pode", "pode sim"}


def is_confirmation_no(text: str) -> bool:
    normalized = normalize_text(text)
    cancel_words = {
        "nao",
        "não",
        "n",
        "cancelar",
        "cancela",
        "cancele",
        "cancelar isso",
        "deixa",
        "deixa pra la",
        "deixa para la",
        "deixa quieto",
        "esquece",
        "sair",
        "voltar",
    }
    return normalized in cancel_words or normalized.startswith(("cancela ", "cancelar ", "cancele "))


def smart_open_choice_kind(text: str) -> str | None:
    normalized = normalize_text(text)
    compact = re.sub(r"[^a-z0-9]", "", normalized)

    if "aplicativo" in normalized or "programa" in normalized:
        return "app"

    if "site" in normalized or "pagina" in normalized or "web" in normalized:
        return "site"

    if compact in APP_CHOICE_ALIASES:
        return "app"

    if compact in SITE_CHOICE_ALIASES:
        return "site"

    app_score = max(
        (difflib.SequenceMatcher(None, compact, alias).ratio() for alias in APP_CHOICE_ALIASES),
        default=0,
    )
    site_score = max(
        (difflib.SequenceMatcher(None, compact, alias).ratio() for alias in SITE_CHOICE_ALIASES),
        default=0,
    )

    if app_score >= 0.78 and app_score > site_score:
        return "app"

    if site_score >= 0.78 and site_score > app_score:
        return "site"

    return None
