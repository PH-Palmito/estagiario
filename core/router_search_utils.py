from __future__ import annotations

import re

from core.router_utils import normalize_text

SEARCH_STOP_WORD_PATTERN = (
    r"\b(?:comandos?|comando|de|para|pra|pode|poderia|consegue|conseguiria|"
    r"pesquisa|pesquise|pesquisar|esquisa|esquise|esquisar|quisa|quise|quisar|"
    r"procure|procurar|buscar|busque|procura|no|na|em|dentro|do|da)\b"
)


def cleanup_marketplace_query(query: str) -> str:
    cleaned = normalize_text(query).strip(" .,:;-")
    replacements = {
        "nutbook": "notebook",
        "notbook": "notebook",
        "notebooke": "notebook",
    }
    return replacements.get(cleaned, cleaned)


def cleanup_site_query(query: str) -> str:
    cleaned = normalize_text(query).strip(" .,:;-")
    cleaned = re.sub(SEARCH_STOP_WORD_PATTERN, " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned


def strip_search_conversation_tail(text: str) -> str:
    raw = str(text or "").strip()
    normalized = normalize_text(raw)
    for pattern in (
        r"\s+(?:e\s+depois|e|ai|aí|depois)\s+(?:me\s+)?(?:da|dá|de|dê|fala|explique|explica|mostra|mostre|resume|resuma|recomenda|recomende)\b",
        r"\s+(?:e\s+depois|e|ai|aí|depois)\s+(?:abre|abra|toca|toque|coloca|coloque|foca|foque|lembre|lembra)\b",
    ):
        match = re.search(pattern, normalized)
        if match:
            return raw[: match.start()].strip(" .,:;-")
    return raw
