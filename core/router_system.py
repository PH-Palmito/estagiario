from __future__ import annotations

import re

from core.router_utils import normalize_text

TEXT_INPUT_PREFIXES = (
    "digitar ",
    "digite ",
    "digita ",
    "escrever ",
    "escreva ",
    "escreve ",
    "ditar ",
    "dita ",
    "colar ",
    "cole ",
    "cola ",
    "inserir texto ",
    "insira texto ",
)


def detect_windows_startup_command(user_input: str):
    lower = normalize_text(user_input)
    if "windows" not in lower and "pc" not in lower and "computador" not in lower:
        return None

    startup_terms = (
        "inicializacao",
        "iniciar junto",
        "iniciar com",
        "abrir junto",
        "abrir com",
        "ligar junto",
        "ligar com",
    )
    if not any(term in lower for term in startup_terms):
        return None

    disable_terms = ("desativ", "deslig", "remov", "tir", "nao iniciar", "parar de iniciar")
    status_terms = ("status", "esta ativ", "ta ativ", "esta lig", "ta lig")

    if any(term in lower for term in disable_terms):
        return {"intent": "windows_startup_disable", "target": None}
    if any(term in lower for term in status_terms):
        return {"intent": "windows_startup_status", "target": None}
    return {"intent": "windows_startup_enable", "target": None}


def detect_run_script(user_input: str):
    lower = normalize_text(user_input)
    for prefix in ["rode o script ", "rode script ", "execute o script ", "execute script ", "executar script "]:
        if lower.startswith(prefix):
            script = user_input[len(prefix):].strip()
            if script:
                return {"intent": "run_script", "target": script}
    return None


def detect_type_text(user_input: str):
    lower = normalize_text(user_input)
    compact_lower = re.sub(r"[:\-]+", " ", lower)
    compact_lower = re.sub(r"\s+", " ", compact_lower).strip()
    for prefix in TEXT_INPUT_PREFIXES:
        if compact_lower.startswith(prefix):
            content = user_input[len(prefix):].strip(" \t,:;-")
            if not content:
                return {
                    "intent": "respond",
                    "target": None,
                    "response": "Qual texto devo inserir?",
                }
            return {"intent": "type_text", "target": None, "content": content}

    return None


SYSTEM_INPUT_DETECTORS = (
    detect_type_text,
)

SYSTEM_DETECTORS = (
    detect_windows_startup_command,
    detect_run_script,
)
