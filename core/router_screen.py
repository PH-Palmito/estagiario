from __future__ import annotations

import re

from core.router_utils import normalize_text

ORDINAL_WORDS = {
    "primeiro": 1,
    "primeira": 1,
    "segundo": 2,
    "segunda": 2,
    "terceiro": 3,
    "terceira": 3,
    "quarto": 4,
    "quarta": 4,
    "quinto": 5,
    "quinta": 5,
    "sexto": 6,
    "sexta": 6,
    "setimo": 7,
    "setima": 7,
    "oitavo": 8,
    "oitava": 8,
    "nono": 9,
    "nona": 9,
    "decimo": 10,
    "decima": 10,
}


def detect_screen_command(user_input: str):
    lower = normalize_text(user_input).strip(" .")

    if lower in {
        "traduzir isso",
        "traduza isso",
        "traduz isso",
        "traduzir esse texto",
        "traduza esse texto",
        "traduz esse texto",
        "traduzir o que li",
        "traduza o que li",
        "traduz o que li",
    }:
        return {"intent": "browser_translate_last_selection", "target": None}

    if re.match(r"^(?:e\s+)?(?:o\s+)?que\s+(?:tem|ta|esta)(?:\s+ai)?\s+na\s+tela$", lower):
        return {"intent": "browser_describe_screen", "target": None}

    if lower in {
        "resuma a tela",
        "resumir tela",
        "resumir a tela",
        "resuma o conteudo",
        "resuma o conteudo da tela",
        "me da um resumo da tela",
        "me de um resumo da tela",
        "qual o resumo da tela",
        "resumo da tela",
        "o que voce ve resumido",
        "o que voce ve na tela resumido",
        "resume",
        "resome",
        "resumida",
        "resumir",
        "resuma",
    }:
        return {"intent": "browser_summarize_screen", "target": None}

    if re.match(r"^resum\w*\s+(?:a\s+)?tela$", lower):
        return {"intent": "browser_summarize_screen", "target": None}

    if lower in {
        "detalha",
        "detalhar",
        "detalha a tela",
        "detalhar a tela",
        "conteudo principal",
        "conteudo principal da tela",
        "o que importa na tela",
        "o que e importante na tela",
        "explique a tela",
        "me explique a tela",
        "quero detalhes da tela",
        "me de detalhes da tela",
        "o que ha na tela em detalhe",
        "explica",
        "explique",
        "explica melhor",
        "me explica melhor",
    }:
        return {"intent": "browser_explain_screen", "target": None}

    if re.match(r"^(?:detalh\w*|explic\w*)\s+(?:a\s+)?tela$", lower):
        return {"intent": "browser_explain_screen", "target": None}

    if lower in {
        "o que tem na tela",
        "que tem na tela",
        "e que tem na tela",
        "ler tela",
        "leia a tela",
        "ler a pagina",
        "leia a pagina",
        "ler texto da pagina",
        "ver texto da pagina",
        "ver o texto da pagina",
        "veja texto da pagina",
        "veja o texto da pagina",
        "leia o texto da pagina",
        "leia texto da pagina",
        "lembre o texto da pagina",
        "ler o texto da pagina",
        "liga o texto da pagina",
        "ligar o texto da pagina",
        "listar links",
        "liste os links",
        "mostrar opcoes",
        "quais botoes",
        "quais botao",
        "quais links",
    }:
        return {"intent": "browser_describe_screen", "target": None}

    if lower in {
        "traduzir selecionado",
        "traduz selecionado",
        "traduza selecionado",
        "traduzir selecao",
        "traduz a selecao",
        "traduza a selecao",
        "traduzir texto selecionado",
        "traduza o texto selecionado",
        "traducao do selecionado",
    }:
        return {"intent": "browser_translate_selection", "target": None}

    if any(token in lower for token in {"traduz", "traduza", "traducao"}) and any(
        token in lower for token in {"selecion", "seleccion", "licion", "isso", "texto"}
    ):
        if "isso" in lower or "que li" in lower:
            return {"intent": "browser_translate_last_selection", "target": None}
        return {"intent": "browser_translate_selection", "target": None}

    if lower in {
        "ler produtos selecionados",
        "ler produto selecionado",
        "leia produtos selecionados",
        "leia os produtos selecionados",
        "extrair produtos selecionados",
        "listar produtos selecionados",
    }:
        return {"intent": "browser_read_selected_products", "target": None}

    if lower in {
        "ler selecionado",
        "leia selecionado",
        "ler selecao",
        "leia a selecao",
        "ler texto selecionado",
        "leia o texto selecionado",
        "o que selecionei",
        "usar selecionado",
        "usar selecao",
        "ler itens selecionados",
        "ler produtos selecionados",
    }:
        return {"intent": "browser_read_selection", "target": None}

    if any(token in lower for token in {"selecion", "seleccion", "licion"}) and any(
        token
        in lower
        for token in {"ler", "leia", "leica", "lig", "link", "links", "item", "itens", "produto", "produtos", "texto", "usar"}
    ):
        return {"intent": "browser_read_selection", "target": None}

    if lower in {
        "ler mais",
        "leia mais",
        "mostrar mais",
        "mostre mais",
        "ver mais",
        "veja mais",
        "continua lendo",
        "continuar lendo",
        "o que mais tem",
        "mais produtos",
        "proximos produtos",
        "proximas opcoes",
        "proximos itens",
    }:
        return {"intent": "browser_read_more", "target": None}

    if lower in {
        "qual o mais barato",
        "qual e o mais barato",
        "me diga o mais barato",
        "mostre o mais barato",
        "comparar precos",
        "compare os precos",
        "menor preco",
        "menor pre o",
        "comparar pre os",
        "compare os pre os",
    }:
        return {"intent": "browser_cheapest_listed_item", "target": None}

    if lower.startswith(("comparar pre", "compare os pre", "comparar os pre")):
        return {"intent": "browser_cheapest_listed_item", "target": None}

    listed_item_match = re.match(
        r"^(?:clicar|clica|clique|abrir|abre|selecionar|selecione|apertar|aperte)\s+(?:no|na|o|a)?\s*(\d+|primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|quint[oa]|sext[oa]|setim[oa]|oitav[oa]|non[oa]|decim[oa])(?:\s+(?:item|produto|resultado|opcao|opcao da lista|link))?$",
        lower,
    )
    if listed_item_match:
        item = listed_item_match.group(1)
        index = int(item) if item.isdigit() else ORDINAL_WORDS.get(item)
        if index:
            return {"intent": "browser_click_listed_item", "target": index}

    info_item_match = re.match(
        r"^(?:informacao|informacoes|informa o|informa es|detalhe|detalhes|fale|me fale|me diga|diga|ver|veja|mostrar|mostre)\s+(?:do|da|de|o|a|sobre\s+o|sobre\s+a)?\s*(\d+|primeir[oa]|segund[oa]|terceir[oa]|quart[oa]|quint[oa]|sext[oa]|setim[oa]|oitav[oa]|non[oa]|decim[oa])(?:\s+(?:item|produto|resultado|opcao|opcao da lista))?$",
        lower,
    )
    if info_item_match:
        item = info_item_match.group(1)
        index = int(item) if item.isdigit() else ORDINAL_WORDS.get(item)
        if index:
            return {"intent": "browser_describe_listed_item", "target": index}

    return None


SCREEN_DETECTORS = [
    detect_screen_command,
]
