from __future__ import annotations

from core.router_utils import normalize_text


def detect_code_inspection_command(user_input: str):
    lower = normalize_text(user_input)

    if lower in {
        "inspecionar selecionado",
        "inspecionar selecao",
        "inspecionar seleção",
        "inspecionar codigo selecionado",
        "inspecionar c digo selecionado",
        "inspecionar c3digo selecionado",
        "inspecionar c3 b3digo selecionado",
        "inspecionar o codigo selecionado",
        "analisar selecionado",
        "analisar selecao",
        "analisar seleção",
        "analisar codigo selecionado",
        "analisar c digo selecionado",
        "analisar o codigo selecionado",
        "revisar codigo selecionado",
        "procurar erro no selecionado",
        "procurar erros no selecionado",
        "procurar erros no codigo selecionado",
    }:
        return {"intent": "code_inspect_selection", "target": None}

    if "selecionado" in lower and ("inspecionar" in lower or "analisar" in lower) and (
        "codigo" in lower or "c digo" in lower or "digo" in lower
    ):
        return {"intent": "code_inspect_selection", "target": None}

    if lower in {
        "inspecionar codigo",
        "inspecionar o codigo",
        "inspecione codigo",
        "inspecione o codigo",
        "inspecionar codigo do projeto",
        "inspecione codigo do projeto",
        "inspecione o codigo do projeto",
        "analisar codigo",
        "analisar o codigo",
        "analise codigo",
        "analise o codigo",
        "revisar codigo",
        "revisar o codigo",
        "verificar codigo",
        "verificar o codigo",
        "verifique codigo",
        "verifique o codigo",
        "procurar erros no codigo",
        "procurar erros no projeto",
        "achar erros no codigo",
        "detectar erros no codigo",
    }:
        return {"intent": "code_inspect_workspace", "target": None}

    for prefix in (
        "inspecionar arquivo ",
        "inspecione o arquivo ",
        "analisar arquivo ",
        "analise o arquivo ",
        "procurar erros no arquivo ",
        "achar erros no arquivo ",
        "revisar arquivo ",
    ):
        if lower.startswith(prefix):
            target = user_input[len(prefix):].strip()
            if target:
                return {"intent": "code_inspect_target", "target": target}

    return None


CODE_DETECTORS = [
    detect_code_inspection_command,
]
