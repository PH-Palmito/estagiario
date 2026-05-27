from __future__ import annotations

import re
from collections.abc import Callable

from core.router_utils import normalize_text
from memory.study import (
    add_study_goal,
    add_study_review,
    complete_study_review,
    format_study_panel,
    log_study_session,
    study_snapshot,
)
from memory.ui_state import update_ui_state


def _refresh_study_snapshot(open_panel: bool = False) -> None:
    patch = {"study_snapshot": study_snapshot()}
    if open_panel:
        patch.update({"active_panel": "estudos", "open_panels": ["estudos"]})
    update_ui_state(patch)


def maybe_handle_study_command(user_input: str, show_hud: Callable[[], str]) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "estudos",
        "painel de estudos",
        "abrir estudos",
        "abrir painel de estudos",
        "mostrar estudos",
        "mostrar painel de estudos",
    }:
        show_hud()
        _refresh_study_snapshot(open_panel=True)
        return "Painel de estudos aberto."

    if normalized in {
        "status dos estudos",
        "progresso dos estudos",
        "meu progresso de estudos",
        "revisoes pendentes",
        "revisoes de estudo",
    }:
        _refresh_study_snapshot(open_panel=True)
        return format_study_panel()

    if normalized.startswith("meta de estudo ") or normalized.startswith("adicionar meta de estudo ") or normalized.startswith("nova meta "):
        result = add_study_goal(user_input)
        _refresh_study_snapshot(open_panel=True)
        return result

    if normalized.startswith("revisar ") or normalized.startswith("adicionar revisao ") or normalized.startswith("nova revisao "):
        result = add_study_review(user_input)
        _refresh_study_snapshot(open_panel=True)
        return result

    review_match = re.match(r"^(?:concluir|marcar)\s+revisao\s+(\d+)$", normalized)
    if review_match:
        result = complete_study_review(review_match.group(1))
        _refresh_study_snapshot(open_panel=True)
        return result

    if normalized in {"concluir revisao", "marcar revisao"}:
        result = complete_study_review("1")
        _refresh_study_snapshot(open_panel=True)
        return result

    if normalized.startswith("estudei ") or normalized.startswith("registrar estudo ") or normalized.startswith("sessao de estudo "):
        result = log_study_session(user_input)
        _refresh_study_snapshot(open_panel=True)
        return result

    return None
