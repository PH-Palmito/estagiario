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
