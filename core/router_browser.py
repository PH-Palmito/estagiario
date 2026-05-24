from __future__ import annotations

import difflib
import re

from core.router_apps import (
    OPEN_PREFIXES,
    _best_fuzzy_match,
    _extract_after_prefix,
    _match_app_target,
    _site_options,
    _strip_leading_articles,
)
from core.router_utils import normalize_text
from memory.current_topic import load_current_topic


def _current_topic_search_query() -> str:
    topic = load_current_topic() or {}
    for key in ("topic", "page_title", "summary"):
        value = str(topic.get(key, "")).strip()
        if value:
            return value
    return ""


def _looks_like_new_tab(text: str) -> bool:
    text = normalize_text(text)

    if not text:
        return False

    direct_phrases = {
        "nova aba",
        "nova ab",
        "nova abra",
        "novo aba",
        "nova",
        "novado",
        "noza",
        "noza abra",
        "abrir nova",
        "abre nova",
    }

    if text in direct_phrases:
        return True

    if difflib.SequenceMatcher(None, text, "nova aba").ratio() >= 0.45:
        return True

    words = text.split()
    if any(word.startswith(("nov", "noz")) for word in words):
        return True

    if "aba" in text or text == "ab":
        return True

    return False


def detect_browser_command(user_input: str):
    lower = normalize_text(user_input)
    current_topic_query = _current_topic_search_query()

    if any(phrase in lower for phrase in {"fecha aba e site", "fechar aba e site", "fecha o site", "fechar o site"}):
        return {"intent": "browser_close_tab", "target": None}

    if lower in {"fecha", "fechar", "fecha ai", "fecha ae"}:
        return {"intent": "context_close", "target": None}

    if lower in {"aba anterior", "anterior"}:
        return {"intent": "browser_prev_tab", "target": None}

    if lower in {"volta", "voltar"}:
        return {"intent": "browser_back", "target": None}

    if lower in {"proxima", "proxima aba", "aba seguinte", "seguinte"} or "proxima aba" in lower:
        return {"intent": "browser_next_tab", "target": None}

    if lower in {"mais uma", "outra aba"}:
        return {"intent": "browser_new_tab", "target": None}

    if lower in {"proxima aba", "aba seguinte"} or "proxima aba" in lower:
        return {"intent": "browser_next_tab", "target": None}

    if lower in {"aba anterior", "voltar aba"} or "aba anterior" in lower:
        return {"intent": "browser_prev_tab", "target": None}

    if any(phrase in lower for phrase in {"nova aba", "nova ab", "nova abra", "novo aba", "abrir nova", "abre nova"}):
        return {"intent": "browser_new_tab", "target": None}

    open_target = _extract_after_prefix(lower, OPEN_PREFIXES)
    if open_target:
        candidate = _strip_leading_articles(open_target)
        if _match_app_target(candidate):
            return None
        if _best_fuzzy_match(candidate, _site_options(), cutoff=0.7):
            return None
        if _looks_like_new_tab(candidate):
            return {"intent": "browser_new_tab", "target": None}

    if lower in {"fechar aba", "fecha aba", "feche a aba", "fecha"} or "fechar aba" in lower:
        return {"intent": "browser_close_tab", "target": None}

    if lower.startswith(("pesquisa por ", "pesquisar por ", "pesquise por ", "esquisar por ", "esquise por ")):
        query = re.sub(r"^(pesquisa|pesquisar|pesquise|esquisar|esquise) por ", "", lower).strip()
        query = re.sub(r"\s+no navegador$", "", query).strip()
        if query in {"mais sobre", "mais sobre isso", "mais sobre esse tema", "mais sobre esse assunto", "isso", "esse tema", "esse assunto"}:
            query = current_topic_query
        if query:
            return {"intent": "browser_search", "target": query}

    if lower.startswith(("pesquisa ", "pesquisar ", "pesquise ", "esquisar ", "esquise ")):
        query = re.sub(r"^(pesquisa|pesquisar|pesquise|esquisar|esquise) ", "", lower).strip()
        query = re.sub(r"\s+no navegador$", "", query).strip()
        if query in {"mais sobre", "mais sobre isso", "mais sobre esse tema", "mais sobre esse assunto", "isso", "esse tema", "esse assunto"}:
            query = current_topic_query
        if query:
            return {"intent": "google_search", "target": query}

    if lower in {
        "pesquise mais sobre",
        "pesquisar mais sobre",
        "pesquisa mais sobre",
        "pesquise mais sobre isso",
        "pesquisar mais sobre isso",
        "pesquisa mais sobre isso",
        "pesquise mais sobre esse tema",
        "pesquise mais sobre esse assunto",
    } and current_topic_query:
        return {"intent": "google_search", "target": current_topic_query}

    return None


BROWSER_DETECTORS = [
    detect_browser_command,
]
