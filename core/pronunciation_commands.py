from __future__ import annotations

import re

from core.router_utils import normalize_text
from memory.tts_pronunciations import (
    get_tts_pronunciation,
    load_tts_pronunciations,
    remove_tts_pronunciation,
    set_tts_pronunciation,
)


def list_pronunciation_response() -> str:
    pronunciations = load_tts_pronunciations()
    if not pronunciations:
        return "Nao ha pronuncias personalizadas salvas."

    items = []
    for term, pronunciation in sorted(pronunciations.items(), key=lambda item: item[0].lower()):
        items.append(f"{term} -> {pronunciation}")
        if len(items) >= 12:
            break

    return "Pronuncias salvas: " + "; ".join(items) + "."


def maybe_handle_pronunciation_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)
    raw = str(user_input or "").strip()

    save_patterns = [
        r"^\s*pronuncia(?:cao)?\s+de\s+(.+?)\s+como\s+(.+?)\s*$",
        r"^\s*pronuncia(?:cao)?\s+de\s+(.+?)\s+para\s+(.+?)\s*$",
        r"^\s*ajustar\s+pronuncia(?:cao)?\s+de\s+(.+?)\s+para\s+(.+?)\s*$",
        r"^\s*salvar\s+pronuncia(?:cao)?\s+de\s+(.+?)\s+como\s+(.+?)\s*$",
        r"^\s*chama\s+(.+?)\s+de\s+(.+?)\s*$",
        r"^\s*fala\s+(.+?)\s+como\s+(.+?)\s*$",
        r"^\s*le\s+(.+?)\s+como\s+(.+?)\s*$",
    ]
    for pattern in save_patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            term = match.group(1).strip(" \t,.:;!?\"'")
            pronunciation = match.group(2).strip(" \t,.:;!?\"'")
            if not term or not pronunciation:
                return "Preciso da palavra e da pronuncia."
            set_tts_pronunciation(term, pronunciation)
            return f"Pronuncia salva para {term}."

    remove_patterns = [
        r"^\s*remover\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
        r"^\s*apagar\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
        r"^\s*tira\s+a\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
        r"^\s*esquece\s+a\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
    ]
    for pattern in remove_patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            term = match.group(1).strip(" \t,.:;!?\"'")
            if not term:
                return "Qual palavra devo remover?"
            removed = remove_tts_pronunciation(term)
            if removed:
                return f"Pronuncia removida para {term}."
            return f"Nao encontrei pronuncia salva para {term}."

    if normalized in {
        "listar pronuncias",
        "listar pronunciacoes",
        "mostrar pronuncias",
        "mostrar pronunciacoes",
        "pronuncias salvas",
        "pronunciacoes salvas",
        "quais pronuncias estao salvas",
        "quais pronunciacoes estao salvas",
    }:
        return list_pronunciation_response()

    query_patterns = [
        r"^\s*qual\s+a\s+pronuncia(?:cao)?\s+de\s+(.+?)\s*$",
        r"^\s*como\s+voce\s+fala\s+(.+?)\s*$",
        r"^\s*como\s+fala\s+(.+?)\s*$",
    ]
    for pattern in query_patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            term = match.group(1).strip(" \t,.:;!?\"'")
            if not term:
                return "Qual palavra voce quer consultar?"
            pronunciation = get_tts_pronunciation(term)
            if pronunciation:
                return f"A pronuncia salva para {term} e {pronunciation}."
            return f"Ainda nao ha pronuncia personalizada para {term}."

    return None
