from __future__ import annotations

import re
from collections.abc import Callable

from core.router_utils import normalize_text
from memory.training import (
    clear_training_injuries,
    format_muscle_status_from_text,
    format_today_workout,
    format_training_status,
    mark_custom_training_for_dates_from_text,
    mark_custom_training_from_text,
    mark_injury_from_text,
    mark_named_workouts_from_text,
    mark_planned_training_from_text,
    mark_training_completed,
    parse_muscles,
    set_training_reminder_from_text,
    skip_today_training,
    training_snapshot,
)
from memory.ui_state import update_ui_state

pending_training_request = ""


def _refresh_training_snapshot() -> None:
    update_ui_state({"training_snapshot": training_snapshot()})


def reset_pending_training_request() -> None:
    global pending_training_request
    pending_training_request = ""


def maybe_handle_training_command(user_input: str, show_training: Callable[[], str]) -> str | None:
    global pending_training_request
    normalized = normalize_text(user_input)

    if pending_training_request and parse_muscles(user_input):
        result = mark_custom_training_for_dates_from_text(user_input, pending_training_request)
        pending_training_request = ""
        _refresh_training_snapshot()
        return result

    if normalized in {
        "treino",
        "treino de hoje",
        "qual o treino de hoje",
        "qual meu treino de hoje",
        "mostrar treino de hoje",
        "ver treino de hoje",
    }:
        _refresh_training_snapshot()
        return format_today_workout()

    if normalized in {
        "status do treino",
        "meu progresso de treino",
        "progresso do treino",
        "status da meta de treino",
        "fadiga muscular",
        "mapa de fadiga",
    }:
        _refresh_training_snapshot()
        return format_training_status()

    if normalized.startswith("status do treino ") or normalized.startswith("fadiga "):
        _refresh_training_snapshot()
        return format_muscle_status_from_text(user_input)

    if normalized in {
        "abrir treino",
        "abrir painel de treino",
        "mostrar painel de treino",
        "mostrar treino no painel",
        "painel treino",
        "painel de treino",
    }:
        return show_training()

    if normalized in {
        "marcar treino concluido",
        "marcar treino como concluido",
        "treino concluido",
        "concluir treino",
        "terminei o treino",
        "finalizei o treino",
    }:
        result = mark_training_completed()
        _refresh_training_snapshot()
        return result

    if (
        ("treino de segunda" in normalized)
        or ("treino da segunda" in normalized)
        or ("treino de terca" in normalized)
        or ("treino da terca" in normalized)
        or ("treino de quinta" in normalized)
        or ("treino da quinta" in normalized)
        or ("treino de sexta" in normalized)
        or ("treino da sexta" in normalized)
        or ("treino de sabado" in normalized)
        or ("treino do sabado" in normalized)
    ) and any(verb in normalized for verb in {"fiz", "treinei", "registrar", "adicionar", "marcar"}):
        result = mark_named_workouts_from_text(user_input)
        _refresh_training_snapshot()
        return result

    if (
        ("treinei" in normalized or "fiz treino" in normalized)
        and re.search(r"\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b", normalized)
        and not parse_muscles(user_input)
    ):
        result = mark_planned_training_from_text(user_input)
        pending_training_request = ""
        _refresh_training_snapshot()
        return result

    if (
        "treinei" in normalized
        or "treino livre" in normalized
        or "treino diferente" in normalized
        or "marcar treino livre" in normalized
        or "registrar treino livre" in normalized
        or (
            ("adicionar treino" in normalized or "registrar treino" in normalized)
            and any(group in normalized for group in {"braco", "bracos", "costas", "peito", "ombro", "core", "abdomen", "perna", "pernas"})
        )
    ):
        result = mark_custom_training_from_text(user_input)
        if result.startswith("Quais grupos voce treinou?"):
            pending_training_request = user_input
        _refresh_training_snapshot()
        return result

    if (
        "adicionar treino" in normalized
        or "registrar treino" in normalized
        or "marcar treino de" in normalized
        or "marcar treino do dia" in normalized
        or "esqueci de marcar treino" in normalized
    ):
        result = mark_planned_training_from_text(user_input)
        _refresh_training_snapshot()
        return result

    if normalized in {"pular treino", "pular treino hoje", "nao treinei hoje", "faltei treino hoje"}:
        result = skip_today_training()
        _refresh_training_snapshot()
        return result

    if normalized in {"limpar lesoes", "limpar lesao", "estou recuperado", "liberar lesoes", "zerar lesoes"}:
        result = clear_training_injuries()
        _refresh_training_snapshot()
        return result

    if any(term in normalized for term in {"lesionei", "machuquei", "me machuquei", "lesao", "lesionado"}):
        result = mark_injury_from_text(user_input)
        _refresh_training_snapshot()
        return result

    if "lembrete" in normalized and "treino" in normalized and re.search(r"\b\d{1,2}(?::|h)?\d{0,2}\b", user_input):
        return set_training_reminder_from_text(user_input)

    return None
