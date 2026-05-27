from __future__ import annotations

from core.command_schema import Command
from core.permission_policy import command_requires_strong_confirmation


def _normalize(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


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
        return normalized == "confirmar"
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
