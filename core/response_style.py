from __future__ import annotations

import re
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

GENERIC_CONFIRMATION_MESSAGES = {
    "Pronto.",
    "Tudo pronto.",
    "Feito.",
    "Ok.",
    "Certo.",
}

OPEN_APP_TARGETS = {
    "Abrindo spotify.": "Spotify",
    "Abrindo chrome.": "Chrome",
    "Abrindo code.": "VS Code",
}

CLOSE_APP_TARGETS = {
    "Fechando spotify.": "Spotify",
    "Fechando code.": "VS Code",
}

ASSISTENTE_OPEN_TEMPLATES = (
    "Perfeitamente. Abrindo {target}.",
    "Abrindo {target}.",
    "Certo. Abrindo {target}.",
)

AXEL_OPEN_TEMPLATES = (
    "Na mao. Abrindo {target}.",
    "Certo. Abrindo {target}.",
    "Abrindo {target}.",
)

JARVIS_OPEN_TEMPLATES = (
    "Certamente. Abrindo {target}.",
    "Abrindo {target}.",
    "Entendido. Abrindo {target}.",
)

CLOSE_TEMPLATES = (
    "Encerrando {target}.",
    "Fechando {target}.",
    "{target} sera encerrado.",
)

ASSISTENTE_STATUS_VARIANTS = {
    "Escuta pausada.": (
        "Escuta em pausa.",
        "Modo escuta pausado.",
        "Pausa de escuta ativada.",
    ),
    "Escuta retomada.": (
        "Escuta restabelecida.",
        "Voltei a ouvir.",
        "Modo escuta retomado.",
    ),
    "Acao cancelada.": (
        "Acao cancelada.",
        "Cancelado.",
        "Tudo bem. Cancelei.",
    ),
}

AXEL_STATUS_VARIANTS = {
    **ASSISTENTE_STATUS_VARIANTS,
    "Encerrando.": (
        "Encerrando por agora.",
        "Vou ficar em espera.",
        "Fechando a sessao por aqui.",
    ),
    "Ok, nao abri.": (
        "Certo. Mantive fechado.",
        "Sem abrir, entao.",
        "Beleza. Deixei como estava.",
    ),
    "Nada para repetir.": (
        "Ainda nao tenho algo recente para repetir.",
        "Nada recente ficou guardado para repetir.",
        "Sem resposta recente no bolso.",
    ),
    "Passo adicionado.": (
        "Passo registrado.",
        "Etapa adicionada.",
        "Anotei esse passo.",
    ),
}

JARVIS_STATUS_VARIANTS = {
    **ASSISTENTE_STATUS_VARIANTS,
    "Encerrando.": (
        "Encerrando por agora.",
        "Ficarei em espera.",
        "Encerrando a sessao.",
    ),
    "Ok, nao abri.": (
        "Certo. Não abri.",
        "Entendido. Mantive fechado.",
        "Sem abrir, entao.",
    ),
    "Nada para repetir.": (
        "Nao ha nada recente para repetir.",
        "Sem resposta recente para repetir.",
        "Ainda nao tenho algo para repetir.",
    ),
    "Passo adicionado.": (
        "Passo registrado.",
        "Etapa adicionada.",
        "Registrei esse passo.",
    ),
}


def _compact(text: str) -> str:
    return re.sub(r"\s+", " ", str(text or "").strip())


def _variant_key(*parts: str) -> str:
    raw = "_".join(str(part or "") for part in parts)
    return re.sub(r"[^a-z0-9]+", "_", raw.lower()).strip("_")


def _format_templates(templates: tuple[str, ...], **fields: str) -> tuple[str, ...]:
    return tuple(template.format(**fields) for template in templates)


def _target_action_response(
    message: str,
    *,
    style: str,
    action: str,
    targets: Mapping[str, str],
    templates: tuple[str, ...],
    next_phrase: NextPhrase,
) -> str | None:
    target = targets.get(message)
    if not target:
        return None
    return next_phrase(
        _variant_key("style", style, action, target),
        _format_templates(templates, target=target),
    )


def _status_response(
    message: str,
    *,
    style: str,
    variants: Mapping[str, tuple[str, ...]],
    next_phrase: NextPhrase,
) -> str | None:
    options = variants.get(message)
    if not options:
        return None
    return next_phrase(_variant_key("style", style, "status", message), options)


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


def avoid_repeating_response(message: str, *, state: MutableMapping[str, object] | None = None) -> str:
    if state is None:
        return message
    compact = _compact(message)
    if "\n" in str(message or "") or len(compact) > 120:
        state["last_styled_response"] = compact
        return message
    last = str(state.get("last_styled_response") or "")
    if compact and compact == last:
        alternatives = (
            "Feito.",
            "Concluido.",
            "Pronto.",
            "Tudo certo.",
        )
        for alternative in alternatives:
            if alternative != last:
                compact = alternative
                break
    state["last_styled_response"] = compact
    return compact


def style_response(
    message: str,
    *,
    preferences: Mapping[str, object],
    variants: Mapping[str, tuple[str, ...]],
    next_phrase: NextPhrase,
    state: MutableMapping[str, object] | None = None,
) -> str:
    assistant_style = str(preferences.get("assistant_style", "")).strip().lower()
    address_user = str(preferences.get("assistant_address_user", "senhor")).strip() or "senhor"
    if assistant_style not in {"axel", "jarvis", "assistente", "elegante"}:
        humor_style = str(preferences.get("assistant_humor_style", "")).strip().lower()
        if bool(preferences.get("assistant_humor_enabled", True)) and humor_style == "jarvis":
            assistant_style = "jarvis"
    if assistant_style not in {"axel", "jarvis", "assistente", "elegante"}:
        return avoid_repeating_response(message, state=state)

    if not bool(preferences.get("assistant_brief_confirmations", True)):
        return avoid_repeating_response(message, state=state)

    if not should_style_response(message):
        return avoid_repeating_response(message, state=state)

    if assistant_style == "axel":
        target_response = _target_action_response(
            message,
            style="axel",
            action="open_app",
            targets=OPEN_APP_TARGETS,
            templates=AXEL_OPEN_TEMPLATES,
            next_phrase=next_phrase,
        )
        if target_response:
            return avoid_repeating_response(target_response, state=state)

        target_response = _target_action_response(
            message,
            style="axel",
            action="close_app",
            targets=CLOSE_APP_TARGETS,
            templates=CLOSE_TEMPLATES,
            next_phrase=next_phrase,
        )
        if target_response:
            return avoid_repeating_response(target_response, state=state)

        status_response = _status_response(
            message,
            style="axel",
            variants=AXEL_STATUS_VARIANTS,
            next_phrase=next_phrase,
        )
        if status_response:
            return avoid_repeating_response(status_response, state=state)

        replacements = {
            "Abrindo spotify.": "Na mao. Abrindo Spotify.",
            "Abrindo chrome.": "Na mao. Abrindo Chrome.",
            "Abrindo code.": "Na mao. Abrindo VS Code.",
            "Fechando spotify.": "Encerrando Spotify.",
            "Fechando code.": "Encerrando VS Code.",
            "Nao entendi.": next_phrase("style_axel_unclear", variants["unclear_command"]),
            "Pode repetir?": next_phrase("style_axel_repeat", variants["repeat_prompt"]),
            "Nao identifiquei o comando.": next_phrase("style_axel_unclear_command", variants["unclear_command"]),
            "Escuta pausada.": "Escuta em pausa.",
            "Escuta retomada.": "Voltei a ouvir.",
            "Acao cancelada.": "Cancelado.",
            "Pode falar.": next_phrase(
                "style_axel_ready_prompt",
                (
                    "Estou ouvindo.",
                    "Pode mandar.",
                    "Manda o alvo.",
                ),
            ),
            "Pode falar...": next_phrase(
                "style_axel_ready_prompt_ellipsis",
                (
                    "Estou ouvindo.",
                    "Pode mandar.",
                    "Manda o alvo.",
                ),
            ),
            "Pode responder...": next_phrase(
                "style_axel_answer_prompt",
                (
                    "Pode responder.",
                    "Estou pronto para a resposta.",
                    "Manda com calma.",
                ),
            ),
            "Encerrando.": "Encerrando por agora.",
            "Modo conversa encerrado. Voltei para comandos.": "Modo conversa encerrado. Voltei aos comandos.",
            "Responda com sim ou nao.": "Preciso so de sim ou nao.",
            "Responda com 'sim' ou 'nao'.": "Preciso so de sim ou nao.",
            "Ok, nao abri.": "Certo. Mantive fechado.",
            "Nada para repetir.": "Ainda nao tenho algo recente para repetir.",
            "Passo adicionado.": "Passo registrado.",
        }
        if message in replacements:
            return avoid_repeating_response(replacements[message], state=state)

        if message in GENERIC_CONFIRMATION_MESSAGES:
            return avoid_repeating_response(
                next_phrase(
                    "style_axel_generic_confirmation",
                    (
                        "Feito.",
                        "Tudo certo.",
                        "Na mao.",
                    ),
                ),
                state=state,
            )

        if message.startswith(ACTION_PREFIXES):
            return avoid_repeating_response(
                next_phrase(
                    "style_axel_action_prefix",
                    (
                        f"Na mao. {message}",
                        f"Certo. {message}",
                        f"Fechado. {message}",
                    ),
                ),
                state=state,
            )

        return avoid_repeating_response(message, state=state)

    if assistant_style in {"assistente", "elegante"}:
        target_response = _target_action_response(
            message,
            style="assistente",
            action="open_app",
            targets=OPEN_APP_TARGETS,
            templates=ASSISTENTE_OPEN_TEMPLATES,
            next_phrase=next_phrase,
        )
        if target_response:
            return avoid_repeating_response(target_response, state=state)

        target_response = _target_action_response(
            message,
            style="assistente",
            action="close_app",
            targets=CLOSE_APP_TARGETS,
            templates=CLOSE_TEMPLATES,
            next_phrase=next_phrase,
        )
        if target_response:
            return avoid_repeating_response(target_response, state=state)

        status_response = _status_response(
            message,
            style="assistente",
            variants=ASSISTENTE_STATUS_VARIANTS,
            next_phrase=next_phrase,
        )
        if status_response:
            return avoid_repeating_response(status_response, state=state)

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
            return avoid_repeating_response(replacements[message], state=state)

        if message in GENERIC_CONFIRMATION_MESSAGES:
            return avoid_repeating_response(
                next_phrase(
                    "style_assistente_generic_confirmation",
                    (
                        "Pronto.",
                        "Tudo certo.",
                        "Feito.",
                    ),
                ),
                state=state,
            )

        if message.startswith(ACTION_PREFIXES):
            return avoid_repeating_response(
                next_phrase(
                    "style_assistente_action_prefix",
                    (
                        f"Perfeitamente. {message}",
                        f"Com certeza. {message}",
                        f"Entendido. {message}",
                    ),
                ),
                state=state,
            )

        return avoid_repeating_response(message, state=state)

    target_response = _target_action_response(
        message,
        style="jarvis",
        action="open_app",
        targets=OPEN_APP_TARGETS,
        templates=JARVIS_OPEN_TEMPLATES,
        next_phrase=next_phrase,
    )
    if target_response:
        return avoid_repeating_response(target_response, state=state)

    target_response = _target_action_response(
        message,
        style="jarvis",
        action="close_app",
        targets=CLOSE_APP_TARGETS,
        templates=CLOSE_TEMPLATES,
        next_phrase=next_phrase,
    )
    if target_response:
        return avoid_repeating_response(target_response, state=state)

    status_response = _status_response(
        message,
        style="jarvis",
        variants=JARVIS_STATUS_VARIANTS,
        next_phrase=next_phrase,
    )
    if status_response:
        return avoid_repeating_response(status_response, state=state)

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
        return avoid_repeating_response(replacements[message], state=state)

    if message in GENERIC_CONFIRMATION_MESSAGES:
        return avoid_repeating_response(
            next_phrase(
                "style_jarvis_generic_confirmation",
                variants.get(
                    "generic_confirmation",
                    (
                        "Pronto.",
                        "Concluido.",
                        "Tudo certo.",
                    ),
                ),
            ),
            state=state,
        )

    if message.startswith(ACTION_PREFIXES):
        return avoid_repeating_response(
            next_phrase(
                "style_jarvis_action_prefix",
                tuple(phrase.format(message=message, address_user=address_user) for phrase in variants["action_prefix"]),
            ),
            state=state,
        )

    return avoid_repeating_response(message, state=state)
