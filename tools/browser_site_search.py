from __future__ import annotations

from urllib.parse import quote_plus


def browser_search_site(site: str, query: str, *, open_url) -> str:
    if not site or not query:
        return "Qual site e qual pesquisa?"

    site = site.strip()
    query = query.strip()

    if "mercadolivre.com.br" in site:
        open_url(f"https://lista.mercadolivre.com.br/{quote_plus(query)}", new=2)
        return f"Pesquisando {query} no Mercado Livre em uma nova aba."

    if "magazineluiza.com.br" in site:
        open_url(f"https://www.magazineluiza.com.br/busca/{quote_plus(query)}/", new=2)
        return f"Pesquisando {query} no Magazine Luiza em uma nova aba."

    if "youtube.com" in site:
        open_url(f"https://www.youtube.com/results?search_query={quote_plus(query)}", new=2)
        return f"Pesquisando {query} no YouTube em uma nova aba."

    open_url(f"https://www.google.com/search?q={quote_plus(query + ' site:' + site)}", new=2)
    return f"Pesquisando {query} em {site} em uma nova aba."
