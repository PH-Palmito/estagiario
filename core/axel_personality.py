from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping, MutableMapping


PERSONALITY_PROFILE = {
    "archetype": "especialista tecnico operacional",
    "professional_ratio": 70,
    "relaxed_ratio": 20,
    "personality_ratio": 10,
}

SENSITIVE_TERMS = {
    "acao",
    "acoes",
    "api key",
    "banco",
    "bolsa",
    "carteira",
    "chave",
    "cripto",
    "dividendo",
    "financeiro",
    "investimento",
    "jcp",
    "juridico",
    "juridica",
    "lucro",
    "medico",
    "medica",
    "patrimonio",
    "rendimento",
    "seguranca",
    "senha",
    "token",
}

ERROR_OR_FRUSTRATION_TERMS = {
    "acesso negado",
    "erro critico",
    "falha critica",
    "nao consegui",
    "nao funcionou",
    "nao funciona",
    "permissao negada",
    "sem permissao",
}

PROACTIVE_SUGGESTIONS = (
    (
        "file_not_found",
        ("arquivo nao encontrado",),
        "Próximo passo útil: procurar pelo nome em Downloads e pastas recentes.",
    ),
    (
        "pdf_pages_missing",
        ("texto salvo no contexto nao veio separado por paginas",),
        "Próximo passo útil: reanalisar o PDF com cache por página.",
    ),
)

HUMOR_OBSERVATIONS = (
    (
        "duplicate_files",
        lambda text: _has_duplicate_file_pattern(text),
        "Todas aparentemente definitivas.",
    ),
    (
        "many_tabs",
        lambda text: "aba" in text and _contains_number_at_least(text, 10),
        "Vou assumir que existe um plano.",
    ),
    (
        "compile_success",
        lambda text: any(
            phrase in text
            for phrase in (
                "build concluido",
                "compilacao concluida",
                "suite completa passou",
                "todos os testes passaram",
            )
        ),
        "Nenhuma lei da física foi violada.",
    ),
    (
        "disk_cleanup",
        lambda text: ("liberado" in text or "liberados" in text) and any(unit in text for unit in (" gb", " mb", "ssd", "disco")),
        "Seu SSD parece satisfeito.",
    ),
)


def _normalize(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", str(text or ""))
    ascii_text = "".join(char for char in ascii_text if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", ascii_text.lower()).strip()


def _contains_number_at_least(text: str, minimum: int) -> bool:
    for raw in re.findall(r"\b\d+\b", text):
        try:
            if int(raw) >= minimum:
                return True
        except ValueError:
            continue
    return False


def _has_duplicate_file_pattern(text: str) -> bool:
    has_file_context = any(term in text for term in ("arquivo", "arquivos", ".pdf", ".docx", ".txt", ".html", ".py"))
    has_duplicate_context = any(term in text for term in ("duplicad", "copia", "versao", "versoes", "final final", "final_final"))
    return has_file_context and has_duplicate_context and (_contains_number_at_least(text, 2) or "duplicad" in text)


def _matches_any(text: str, terms: set[str]) -> bool:
    return any(term in text for term in terms)


def _last_addition_key(state: MutableMapping[str, object] | None) -> str:
    if state is None:
        return ""
    return str(state.get("last_personality_addition_key") or "")


def _remember_addition(state: MutableMapping[str, object] | None, key: str) -> None:
    if state is not None:
        state["last_personality_addition_key"] = key


def personality_enabled(preferences: Mapping[str, object] | None) -> bool:
    if preferences is None:
        return True
    return bool(preferences.get("assistant_personality_enabled", True))


def proactivity_enabled(preferences: Mapping[str, object] | None) -> bool:
    if preferences is None:
        return True
    return bool(preferences.get("assistant_proactivity_enabled", True))


def humor_enabled(preferences: Mapping[str, object] | None) -> bool:
    if preferences is None:
        return True
    if not bool(preferences.get("assistant_humor_enabled", True)):
        return False
    style = str(preferences.get("assistant_humor_style", "seco") or "seco").strip().lower()
    if style == "neutro":
        return False
    try:
        level = int(preferences.get("assistant_humor_level", 2) or 0)
    except (TypeError, ValueError):
        level = 2
    return level >= 2


def contextual_proactive_suggestion(message: str, *, state: MutableMapping[str, object] | None = None) -> tuple[str, str] | None:
    normalized = _normalize(message)
    if not normalized or "proximo passo util" in normalized:
        return None
    for key, triggers, suggestion in PROACTIVE_SUGGESTIONS:
        if key == _last_addition_key(state):
            continue
        if any(trigger in normalized for trigger in triggers):
            return key, suggestion
    return None


def contextual_humor_observation(
    message: str,
    *,
    preferences: Mapping[str, object] | None = None,
    state: MutableMapping[str, object] | None = None,
) -> tuple[str, str] | None:
    normalized = _normalize(message)
    if not normalized:
        return None
    if _matches_any(normalized, SENSITIVE_TERMS) or _matches_any(normalized, ERROR_OR_FRUSTRATION_TERMS):
        return None
    if not humor_enabled(preferences):
        return None
    for key, matcher, observation in HUMOR_OBSERVATIONS:
        if key == _last_addition_key(state):
            continue
        if observation.lower() in message.lower():
            continue
        if matcher(normalized):
            return key, observation
    return None


def _append_sentence(message: str, addition: str) -> str:
    text = str(message or "").strip()
    addition = str(addition or "").strip()
    if not text or not addition:
        return text
    if text.endswith(addition):
        return text
    if text[-1] not in ".!?:;)]}":
        text += "."
    return f"{text} {addition}"


def apply_personality_layer(
    message: str,
    *,
    preferences: Mapping[str, object] | None = None,
    state: MutableMapping[str, object] | None = None,
) -> str:
    if not personality_enabled(preferences):
        return str(message or "").strip()

    text = str(message or "").strip()
    if not text:
        return text

    if proactivity_enabled(preferences):
        suggestion = contextual_proactive_suggestion(text, state=state)
        if suggestion:
            key, addition = suggestion
            _remember_addition(state, key)
            return _append_sentence(text, addition)

    observation = contextual_humor_observation(text, preferences=preferences, state=state)
    if observation:
        key, addition = observation
        _remember_addition(state, key)
        return _append_sentence(text, addition)

    return text
