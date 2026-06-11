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


def detect_power_command(user_input: str):
    lower = normalize_text(user_input)
    lower = re.sub(r"^\s*axel\s+", "", lower).strip(" .")

    if lower in {
        "cancelar desligamento",
        "cancela desligamento",
        "abortar desligamento",
        "aborte desligamento",
        "nao desligue o pc",
        "nao desligar o pc",
    }:
        return {"intent": "system_shutdown_cancel", "target": None}

    device_terms = ("pc", "computador", "windows", "maquina")
    shutdown_terms = ("desligue", "desligar", "desliga", "apague", "apagar")
    if any(term in lower for term in shutdown_terms) and any(term in lower for term in device_terms):
        return {"intent": "system_shutdown", "target": None}
    return None


def detect_background_status_command(user_input: str):
    lower = normalize_text(user_input)
    notification_terms = (
        "notificacoes do background",
        "notificacoes de background",
        "notificacoes em segundo plano",
        "avisos do background",
        "avisos em segundo plano",
    )
    if any(term in lower for term in notification_terms):
        return {"intent": "background_notifications", "target": None}

    latest_terms = (
        "resultado da ultima tarefa",
        "resultado do ultimo background",
        "ultima tarefa em segundo plano",
        "ultimo resultado em segundo plano",
        "ultimo resultado do background",
        "o que terminou em segundo plano",
    )
    if any(term in lower for term in latest_terms):
        return {"intent": "background_latest_result", "target": None}

    background_terms = (
        "segundo plano",
        "background",
        "tarefas em andamento",
        "tarefas rodando",
        "processos do axel",
    )
    status_terms = ("status", "como estao", "listar", "mostre", "ver")
    if any(term in lower for term in background_terms) and any(term in lower for term in status_terms):
        return {"intent": "background_status", "target": None}
    return None


def detect_whatsapp_bridge_command(user_input: str):
    lower = normalize_text(user_input)
    if lower in {
        "status do whatsapp",
        "status da ponte whatsapp",
        "status whatsapp local",
        "ponte whatsapp",
    }:
        return {"intent": "whatsapp.status", "target": None}
    if lower in {
        "iniciar whatsapp local",
        "iniciar ponte whatsapp",
        "ligar ponte whatsapp",
        "ativar ponte whatsapp",
        "iniciar ponte local do whatsapp",
    }:
        return {"intent": "whatsapp.start_local_bridge", "target": None}
    for prefix in (
        "simular whatsapp ",
        "testar whatsapp ",
        "simular mensagem whatsapp ",
    ):
        if lower.startswith(prefix):
            text = user_input[len(prefix):].strip()
            if text:
                return {"intent": "whatsapp.simulate_message", "target": text}
    return None


def detect_telegram_bridge_command(user_input: str):
    lower = normalize_text(user_input)
    if lower in {
        "status do telegram",
        "status telegram",
        "status do bot telegram",
        "telegram bot",
        "bot telegram",
    }:
        return {"intent": "telegram.status", "target": None}
    if lower in {
        "chat id telegram",
        "id telegram",
        "descobrir chat id telegram",
        "descobrir id telegram",
        "listar chats telegram",
        "chats recentes telegram",
    }:
        return {"intent": "telegram.recent_chats", "target": None}
    if lower in {
        "iniciar telegram",
        "iniciar bot telegram",
        "ligar telegram",
        "ligar bot telegram",
        "ativar telegram",
        "ativar bot telegram",
        "iniciar telegram bot",
    }:
        return {"intent": "telegram.start_bot", "target": None}
    for prefix in (
        "simular telegram ",
        "testar telegram ",
        "simular mensagem telegram ",
    ):
        if lower.startswith(prefix):
            text = user_input[len(prefix):].strip()
            if text:
                return {"intent": "telegram.simulate_message", "target": text}
    return None


def detect_keyboard_led_command(user_input: str):
    lower = normalize_text(user_input)
    if "led" not in lower or "teclado" not in lower:
        return None

    if any(term in lower for term in {"status", "estado", "como esta"}):
        return {"intent": "keyboard_led_status", "target": None}
    if any(term in lower for term in {"deslig", "apagar", "off"}):
        return {"intent": "keyboard_led_off", "target": None}

    colors = (
        "vermelho",
        "verde",
        "azul",
        "branco",
        "amarelo",
        "roxo",
        "rosa",
        "ciano",
    )
    effects = ("static", "fixo", "pulso", "respirar", "alerta", "foco", "escuta")
    target = {
        "color": next((color for color in colors if color in lower), ""),
        "profile": "",
        "effect": next((effect for effect in effects if effect in lower), ""),
    }
    if "perfil" in lower:
        match = re.search(r"perfil\s+([\w-]+)", lower)
        if match:
            target["profile"] = match.group(1)
    if any(term in lower for term in {"lig", "acender", "ativar", "on"}):
        return {"intent": "keyboard_led_on", "target": target}
    return {"intent": "keyboard_led_set", "target": target}


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
    detect_power_command,
    detect_background_status_command,
    detect_telegram_bridge_command,
    detect_keyboard_led_command,
    detect_whatsapp_bridge_command,
    detect_run_script,
)
