from __future__ import annotations

from collections.abc import Callable, Mapping, MutableMapping

NextPhrase = Callable[[str, tuple[str, ...]], str]

ACTION_PREFIXES = (
    "Abrindo ",
    "Fechando ",
    "Maximizando ",
    "Minimizando ",
    "Restaurando ",
    "Focando ",
    "Pesquisando ",
    "Rolando ",
    "Procurando ",
    "Tocando ",
    "Pausando ",
)

PREFIXES_TO_KEEP = (
    "Texto selecionado:",
    "Traduzi:",
    "Li selecionado:",
    "Consegui ler",
    "Vejo na tela:",
    "Diagnostico",
    "Correcoes de voz:",
    "Rotinas:",
    "Macros:",
    "Arquivo",
    "Erro",
)


def should_style_response(message: str) -> bool:
    if not message or "\n" in message or len(message) > 120:
        return False
    return not message.startswith(PREFIXES_TO_KEEP)


def next_style_variant(options: tuple[str, ...], state: MutableMapping[str, int]) -> str:
    if not options:
        return ""
    index = int(state.get("style_variation_index", 0))
    choice = options[index % len(options)]
    state["style_variation_index"] = index + 1
    return choice


def style_response(
    message: str,
    *,
    preferences: Mapping[str, object],
    variants: Mapping[str, tuple[str, ...]],
    next_phrase: NextPhrase,
) -> str:
    assistant_style = str(preferences.get("assistant_style", "")).strip().lower()
    address_user = str(preferences.get("assistant_address_user", "senhor")).strip() or "senhor"
    if assistant_style not in {"jarvis", "assistente", "elegante"}:
        humor_style = str(preferences.get("assistant_humor_style", "")).strip().lower()
        if bool(preferences.get("assistant_humor_enabled", True)) and humor_style == "jarvis":
            assistant_style = "jarvis"
    if assistant_style not in {"jarvis", "assistente", "elegante"}:
        return message

    if not bool(preferences.get("assistant_brief_confirmations", True)):
        return message

    if not should_style_response(message):
        return message

    if assistant_style in {"assistente", "elegante"}:
        replacements = {
            "Abrindo spotify.": "Perfeitamente. Abrindo Spotify.",
            "Abrindo chrome.": "Perfeitamente. Abrindo Chrome.",
            "Abrindo code.": "Perfeitamente. Abrindo VS Code.",
            "Fechando spotify.": "Encerrando Spotify.",
            "Fechando code.": "Encerrando VS Code.",
            "Nao entendi.": next_phrase("style_assistente_unclear", variants["unclear_command"]),
            "Pode repetir?": next_phrase("style_assistente_repeat", variants["repeat_prompt"]),
            "Nao identifiquei o comando.": "Não identifiquei o comando.",
            "Escuta pausada.": "Escuta em pausa.",
            "Escuta retomada.": "Escuta restabelecida.",
            "Acao cancelada.": "Ação cancelada.",
        }
        if message in replacements:
            return replacements[message]

        if message.startswith(ACTION_PREFIXES):
            return next_phrase(
                "style_assistente_action_prefix",
                (
                    f"Perfeitamente. {message}",
                    f"Com certeza. {message}",
                    f"Entendido. {message}",
                ),
            )

        return message

    replacements = {
        "Abrindo spotify.": "Certamente. Abrindo Spotify.",
        "Abrindo chrome.": "Certamente. Abrindo Chrome.",
        "Abrindo code.": "Certamente. Abrindo VS Code.",
        "Fechando spotify.": "Encerrando Spotify.",
        "Fechando code.": "Encerrando VS Code.",
        "Nao entendi.": next_phrase("style_jarvis_unclear", variants["unclear_command"]),
        "Pode repetir?": next_phrase("style_jarvis_repeat", variants["repeat_prompt"]),
        "Nao identifiquei o comando.": next_phrase("style_jarvis_unclear_command", variants["unclear_command"]),
        "Escuta pausada.": "Escuta em pausa.",
        "Escuta retomada.": "Escuta restabelecida.",
        "Acao cancelada.": "Ação cancelada.",
        "Pode falar.": next_phrase(
            "style_ready_prompt",
            (
                *tuple(phrase.format(address_user=address_user) for phrase in variants["ready_prompt_addressed"]),
                *variants["ready_prompt"],
            ),
        ),
        "Pode falar...": next_phrase(
            "style_ready_prompt_ellipsis",
            (
                *tuple(phrase.format(address_user=address_user) for phrase in variants["ready_prompt_addressed"]),
                *variants["ready_prompt"],
            ),
        ),
        "Pode responder...": next_phrase(
            "style_answer_prompt",
            (
                f"Pode responder, {address_user}.",
                "Pode responder.",
                "Estou pronto para a resposta.",
            ),
        ),
        "Encerrando.": "Encerrando por agora.",
        "Modo conversa encerrado. Voltei para comandos.": "Modo conversa encerrado. Voltei aos comandos.",
        "Responda com sim ou nao.": "Preciso apenas de sim ou não.",
        "Responda com 'sim' ou 'nao'.": "Preciso apenas de sim ou não.",
        "Responda com app, site ou cancelar.": "Responda com app, site ou cancelar.",
        "Responda com 'app' ou 'site'.": "Responda com app ou site.",
        "Ok, nao abri.": "Certo. Não abri.",
        "Nao consegui entender a resposta. Cancelei essa pergunta.": "Não consegui confirmar a resposta. Cancelei essa pergunta.",
        "Nada para repetir.": "Não há nada recente para repetir.",
        "Passo adicionado.": "Passo registrado.",
    }
    if message in replacements:
        return replacements[message]

    if message.startswith(ACTION_PREFIXES):
        return next_phrase(
            "style_jarvis_action_prefix",
            tuple(phrase.format(message=message, address_user=address_user) for phrase in variants["action_prefix"]),
        )

    return message
