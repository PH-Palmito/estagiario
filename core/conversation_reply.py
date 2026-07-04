from __future__ import annotations

import difflib
from collections.abc import Callable

from memory.assistant_customization import get_axel_introduction
from core.router_conversation import (
    _looks_like_weak_open_response,
    detect_builtin_general_answer,
    practical_question_response,
    remember_useful_conversation_topic,
    useful_conversation_response,
)
from core.router_utils import normalize_text

ChatResponse = Callable[[str], str]


def conversation_reply(user_input: str, chat_response: ChatResponse) -> str:
    normalized = normalize_text(user_input).strip(" .!?")

    if not normalized:
        return "Estou aqui."

    if "um dois" in normalized or "testando" in normalized or "teste de microfone" in normalized:
        return "Teste de microfone recebido. Estou te ouvindo."

    if normalized in {"exatamente", "isso", "isso ai", "e isso ai", "aham", "sim", "boa"} or (
        "isso" in normalized and len(normalized.split()) <= 3
    ):
        return "Peguei."

    if "tudo bem" in normalized or "como voce" in normalized or "como vc" in normalized:
        response = chat_response(user_input)
        return response or "Tudo bem por aqui. E você?"

    if "bom dia" in normalized:
        response = chat_response(user_input)
        return response or "Bom dia."

    if "boa tarde" in normalized:
        response = chat_response(user_input)
        return response or "Boa tarde."

    if "boa noite" in normalized:
        response = chat_response(user_input)
        return response or "Boa noite."

    if normalized in {
        "se apresente",
        "se apresenta",
        "apresentese",
        "apresente se",
        "apresenta se",
        "quem e o axel",
        "quem e axel",
        "fale de voce",
        "fala de voce",
        "conte quem voce e",
        "conta quem voce e",
    }:
        return get_axel_introduction()

    if difflib.SequenceMatcher(None, normalized, "qual o seu nome").ratio() >= 0.78:
        return "Meu nome é Axel."

    if any(phrase in normalized for phrase in {"quantos anos voce tem", "voce nasceu quando", "voce e novo"}):
        return "Bem, eu nasci ontem. Metaforicamente, pelo menos. Ainda estou aprendendo a ser útil sem tropeçar nos cadarços."

    if any(phrase in normalized for phrase in {"voce pensa", "voce sente", "voce e consciente"}):
        return "Ainda não chamaria isso de consciência. Por enquanto, sou mais uma coleção organizada de impulsos tentando ser prestativa."

    builtin = detect_builtin_general_answer(user_input)
    if builtin:
        response = str(builtin.get("response") or "").strip()
        if response:
            return response

    useful = useful_conversation_response(user_input)
    practical = practical_question_response(user_input)
    fallback = useful or practical

    response = chat_response(user_input)
    if response and not (fallback and _looks_like_weak_open_response(response)):
        return response

    if fallback:
        remember_useful_conversation_topic(user_input, fallback)
        return fallback

    return "Acho que eu ouvi meio torto. Repete de outro jeito?"
