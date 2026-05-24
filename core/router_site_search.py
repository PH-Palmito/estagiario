from __future__ import annotations

import re

from core.router_apps import _best_fuzzy_match, _site_options, _strip_leading_articles
from core.router_search_utils import cleanup_marketplace_query
from core.router_utils import normalize_text


def _match_site_target(text: str):
    sites = _site_options()
    target = _strip_leading_articles(normalize_text(text))
    site = _best_fuzzy_match(target, sites, cutoff=0.65)
    if site:
        return site
    return target


def detect_site_search_command(user_input: str):
    lower = normalize_text(user_input).strip(" .")

    if lower in {"que no mercado livre", "no mercado livre"}:
        return {"intent": "respond", "target": None, "response": "Qual produto voce quer pesquisar no Mercado Livre?"}

    polite_site_search_match = re.match(
        r"^(?:pode|poderia|consegue|conseguiria|da para|daria para)\s+(?:pesquisar|pesquise|pesquisa|esquisar|esquise|esquisa|quisar|quise|quisa|procurar|procure|buscar|busque)\s+(.+?)\s+(?:no|na|em|dentro\s+do|dentro\s+da)\s+(.+)$",
        lower,
    )
    if polite_site_search_match:
        query = cleanup_marketplace_query(polite_site_search_match.group(1))
        return {
            "intent": "browser_search_site",
            "target": {
                "query": query,
                "site": _match_site_target(polite_site_search_match.group(2).strip()),
            },
        }

    site_search_match = re.match(
        r"^(?:pesquisa|pesquise|pesquisar|esquisa|esquise|esquisar|quisa|quise|quisar|procure|procurar|buscar|busque)\s+(.+?)\s+(?:no|na|em|dentro\s+do|dentro\s+da)\s+(.+)$",
        lower,
    )
    if site_search_match:
        query = cleanup_marketplace_query(site_search_match.group(1))
        return {
            "intent": "browser_search_site",
            "target": {
                "query": query,
                "site": _match_site_target(site_search_match.group(2).strip()),
            },
        }

    return None


SITE_SEARCH_DETECTORS = [
    detect_site_search_command,
]
