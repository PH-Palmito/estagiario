from __future__ import annotations

from core.command_schema import Command

STRONG_CONFIRMATION_ACTIONS = {
    "close_app",
    "smart_close_app",
    "run_script",
    "type_text",
    "windows_startup_enable",
    "windows_startup_disable",
    "browser_close_tab",
    "browser_click_center",
    "browser_click_text",
    "browser_click_listed_item",
    "vision_download_light_model",
    "file_create",
    "file_write",
    "file_append",
    "file_replace",
    "file_delete",
    "file_copy",
    "file_move",
    "file_rename",
    "folder_create",
    "run_macro",
}

STRONG_CONFIRMATION_TOOL_NAMES = {
    "close_app",
    "smart_close_app",
    "run_script",
    "type_text",
    "windows_startup_enable",
    "windows_startup_disable",
    "browser_close_tab",
    "browser_click_center",
    "browser_click_text",
    "browser_click_listed_item",
    "vision_download_light_model",
    "file_create",
    "file_write",
    "file_append",
    "file_replace",
    "file_delete",
    "file_copy",
    "file_move",
    "file_rename",
    "folder_create",
    "run_macro",
}

STRONG_CONFIRMATION_CATEGORIES = {"files", "system", "browser", "automation"}


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def command_requires_strong_confirmation(command: Command) -> bool:
    action = str(getattr(command, "action", "") or "")
    if action in STRONG_CONFIRMATION_ACTIONS:
        return True

    if action != "action_tool_execute":
        return False

    params = getattr(command, "params", {}) or {}
    tool_name = str(params.get("name") or "").strip()
    if tool_name in STRONG_CONFIRMATION_TOOL_NAMES:
        return True

    try:
        from actions import ensure_default_actions, get_action

        ensure_default_actions()
        spec = get_action(tool_name)
    except Exception:
        spec = None

    if not spec:
        return False

    return bool(spec.requires_confirmation and spec.category in STRONG_CONFIRMATION_CATEGORIES)


def confirmation_instruction(command: Command) -> str:
    if command_requires_strong_confirmation(command):
        return "Para confirmar, responda exatamente: confirmar."
    return "Responda com sim ou nao."


def confirmation_prompt(command: Command) -> str:
    action = getattr(command, "action", "")
    params = getattr(command, "params", {}) or {}
    if command_requires_strong_confirmation(command):
        return f"Acao sensivel: {action} com {params}. Para executar, responda exatamente: confirmar."
    return f"Confirma a acao {action} com {params}?"


def is_confirmation_accepted(text: str, command: Command) -> bool:
    normalized = _normalize(text)
    if command_requires_strong_confirmation(command):
        return normalized in {"confirmar", "confirmo"}
    return normalized in {"sim", "s", "confirmar", "confirmo", "ok", "pode", "pode sim"}


def is_confirmation_rejected(text: str) -> bool:
    normalized = _normalize(text)
    cancel_words = {
        "nao",
        "não",
        "n",
        "cancelar",
        "cancela",
        "cancele",
        "cancelado",
        "cancelar isso",
        "deixa",
        "deixa pra la",
        "deixa para la",
        "deixa quieto",
        "esquece",
        "sair",
        "voltar",
    }
    return normalized in cancel_words or normalized.startswith(("cancela ", "cancelar ", "cancele "))
