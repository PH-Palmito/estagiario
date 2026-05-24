from __future__ import annotations

import re

from core.router_utils import normalize_text


def detect_browser_control_command(user_input: str):
    lower = normalize_text(user_input).strip(" .")

    if any(phrase in lower for phrase in {
        "rolar para baixo",
        "rolar tela para baixo",
        "role tela para baixo",
        "role para baixo",
        "role a tela para baixo",
        "desce a tela",
        "descer a tela",
        "desca a tela",
        "desce na tela",
        "descer na tela",
        "desuna a tela",
        "desum na tela",
        "desuna na tela",
        "desum a tela",
        "desliza para baixo",
        "deslize para baixo",
        "deslizar para baixo",
        "mais para baixo",
        "rolar mais",
        "descer mais",
        "continua descendo",
        "continuar descendo",
        "pagina para baixo",
        "olhe a tela para baixo",
        "olhe para baixo",
        "ola para baixo",
        "ol para baixo",
    }):
        return {"intent": "browser_scroll_down", "target": None}

    if any(phrase in lower for phrase in {
        "descer um pouco",
        "desce um pouco",
        "rolar um pouco",
        "role um pouco",
        "um pouco para baixo",
        "pouco para baixo",
    }):
        return {"intent": "browser_scroll_down_small", "target": None}

    if any(phrase in lower for phrase in {
        "rolar para cima",
        "rolar tela para cima",
        "role tela para cima",
        "role para cima",
        "role a tela para cima",
        "sobe a tela",
        "subir a tela",
        "sobe na tela",
        "subir na tela",
        "desliza para cima",
        "deslize para cima",
        "deslizar para cima",
        "mais para cima",
        "subir mais",
        "continua subindo",
        "continuar subindo",
        "pagina para cima",
        "olhe a tela para cima",
        "olhe para cima",
        "ola para cima",
        "ol para cima",
    }):
        return {"intent": "browser_scroll_up", "target": None}

    if any(phrase in lower for phrase in {
        "subir um pouco",
        "sobe um pouco",
        "um pouco para cima",
        "pouco para cima",
    }):
        return {"intent": "browser_scroll_up_small", "target": None}

    if lower in {"ir para o topo", "vai para o topo", "topo da pagina", "topo", "inicio da pagina", "comeco da pagina", "começo da pagina"}:
        return {"intent": "browser_scroll_top", "target": None}

    if lower in {
        "ir para o fim",
        "vai para o fim",
        "fim da pagina",
        "final da pagina",
        "fim da tela",
        "final da tela",
        "ate o final",
        "ate o fim",
        "rolar ate o final",
        "rolar tela ate o final",
        "olhe a tela ate o final da tela",
        "ir ate o final da tela",
        "vai ate o final da tela",
        "fim",
    }:
        return {"intent": "browser_scroll_bottom", "target": None}

    if lower in {"voltar pagina", "voltar no site", "voltar no navegador", "pagina anterior", "volta pagina", "volta no site"}:
        return {"intent": "browser_back", "target": None}

    if lower in {"avancar pagina", "avancar no site", "avancar no navegador", "pagina seguinte", "vai pra frente", "vai para frente"}:
        return {"intent": "browser_forward", "target": None}

    if lower in {"atualizar pagina", "atualiza pagina", "recarregar pagina", "recarrega pagina", "refresh", "atualizar"}:
        return {"intent": "browser_refresh", "target": None}

    if any(phrase in lower for phrase in {
        "abrir primeiro resultado",
        "abre primeiro resultado",
        "abrir o primeiro resultado",
        "abre o primeiro resultado",
        "primeiro resultado",
        "abrir primeiro link",
        "abre primeiro link",
        "abrir o primeiro link",
        "abre o primeiro link",
        "primeiro link",
    }):
        return {"intent": "browser_open_first_result", "target": None}

    if lower in {"abrir selecionado", "abre selecionado", "abrir item", "abre item", "entrar", "enter"}:
        return {"intent": "browser_open_focused_item", "target": None}

    if lower in {"clicar no centro", "clique no centro", "clica no centro", "clicar na pagina", "clique na pagina"}:
        return {"intent": "browser_click_center", "target": None}

    click_match = re.match(
        r"^(?:clicar|clica|clique|selecionar|selecione|apertar|aperte)\s+(?:(?:em|no|na|o|a)\s+)?(.+)$",
        lower,
    )
    if click_match:
        target = click_match.group(1).strip()
        if target and target not in {"centro", "pagina", "tela"}:
            return {"intent": "browser_click_text", "target": target}

    if lower in {
        "zoom",
        "aumentar zoom",
        "aumenta zoom",
        "mais zoom",
        "zoom mais",
        "ampliar tela",
        "ampliar a tela",
        "amplia tela",
        "amplia a tela",
        "umpliar a tela",
        "umpliar a teoria",
        "ampliar a teoria",
    }:
        return {"intent": "browser_zoom_in", "target": None}

    if lower in {"diminuir zoom", "diminui zoom", "menos zoom", "zoom menos"}:
        return {"intent": "browser_zoom_out", "target": None}

    if lower in {"resetar zoom", "restaurar zoom", "zoom normal", "voltar zoom"}:
        return {"intent": "browser_zoom_reset", "target": None}

    find_match = re.match(r"^(?:procurar|procure|buscar|busque|encontre)\s+(.+?)\s+(?:na|nesta|nessa)\s+pagina$", lower)
    if find_match:
        return {"intent": "browser_find", "target": find_match.group(1).strip()}

    return None


BROWSER_CONTROL_DETECTORS = [
    detect_browser_control_command,
]
