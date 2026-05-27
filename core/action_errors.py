from __future__ import annotations

from typing import Any

ERROR_CATEGORY_MESSAGES = {
    "browser": (
        "Nao consegui concluir a acao no navegador.",
        "Verifique se Edge/Chrome esta aberto, com uma pagina carregada, e tente novamente.",
    ),
    "files": (
        "Nao consegui acessar o arquivo ou pasta.",
        "Confira o caminho, permissao e se o arquivo nao esta aberto por outro programa.",
    ),
    "vision": (
        "Nao consegui concluir a leitura visual.",
        "Verifique se ha uma tela ou imagem visivel e tente novamente.",
    ),
    "network": (
        "Nao consegui acessar o servico externo agora.",
        "Verifique a conexao, token/API key e tente novamente em instantes.",
    ),
    "investments": (
        "Nao consegui atualizar ou ler os dados da carteira.",
        "Confira navegador, rede e o ultimo snapshot salvo.",
    ),
}

ACTION_CATEGORY_HINTS = {
    "weather": "network",
    "news": "network",
    "browser": "browser",
    "image": "vision",
    "vision": "vision",
    "file": "files",
    "folder": "files",
    "investment": "investments",
}


def _compact_error(error: Any, max_chars: int = 220) -> str:
    text = " ".join(str(error or "").split()).strip()
    if not text:
        return ""
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0].rstrip(" ,.;") + "..."


def infer_error_category(action: str, category: str = "") -> str:
    explicit = str(category or "").strip().lower()
    if explicit in ERROR_CATEGORY_MESSAGES:
        return explicit

    action_name = str(action or "").strip().lower()
    for prefix, mapped in ACTION_CATEGORY_HINTS.items():
        if action_name.startswith(prefix) or f".{prefix}" in action_name:
            return mapped
    return explicit or "general"


def format_action_failure_message(action: str, category: str = "", error: Any = "") -> str:
    action_name = str(action or "acao").strip() or "acao"
    resolved_category = infer_error_category(action_name, category)
    detail = _compact_error(error)

    if resolved_category in ERROR_CATEGORY_MESSAGES:
        intro, hint = ERROR_CATEGORY_MESSAGES[resolved_category]
        message = f"{intro} Action: {action_name}. {hint}"
    else:
        message = f"Nao consegui executar a action {action_name}."

    if detail:
        message += f" Detalhe tecnico: {detail}"
    return message
