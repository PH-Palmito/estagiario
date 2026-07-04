from __future__ import annotations

import re
from collections.abc import Callable

from core.router_utils import normalize_text
from core.study_file_analysis import (
    analyze_study_files,
    answer_study_followup,
    current_study_context_matches_study_panel,
    parse_study_file_command,
    polish_study_response,
    request_is_study_or_practice,
    run_study_file_self_test,
)
from memory.study_context import clear_study_context
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


def _refresh_study_snapshot_for_current_file(request: str) -> None:
    if current_study_context_matches_study_panel(request=request):
        _refresh_study_snapshot(open_panel=False)


def _study_response_has_corrupted_text(response: str) -> bool:
    normalized = str(response or "").replace("\x00", "").lower()
    if len(normalized) < 80:
        return False

    suspicious_patterns = [
        r"\bt\s+m\s+s\s+t\s+m\s+s\b",
        r"\bq\s+u\s+i\s+t\s+q\s+l\s+i\s+l\s+m\b",
        r"\bs\s+o\s+n\s+t\s+w\s+i\s+r\s+m\b",
        r"\bqum\b",
        r"\blm\b",
        r"\bciqxi\b",
        r"\btmstm?s?\b",
        r"\bcisos\b",
        r"\bvitorms?\b",
        r"\bcouxtmx",
        r"\bquivtos?\b",
        r"\btrivsn",
        r"\bqvv[aã]t",
    ]
    hits = sum(len(re.findall(pattern, normalized, flags=re.I)) for pattern in suspicious_patterns)
    return hits >= 6


def _block_corrupted_study_response(response: str) -> str:
    if not _study_response_has_corrupted_text(response):
        return response
    return polish_study_response(
        "Nao vou resumir esse arquivo ainda: a extracao retornou texto corrompido "
        "e falhou na verificacao de confianca. Para esse PDF, preciso de OCR externo "
        "confiavel, como um provider estilo ClawHub/PDF OCR, ou de uma versao exportada "
        "como texto pesquisavel."
    )


def _is_general_study_help_request(normalized: str) -> bool:
    if not normalized:
        return False
    if any(
        term in normalized
        for term in {
            "arquivo",
            "documento",
            "pdf",
            "slide",
            "slides",
            "anexo",
            "pagina",
            "página",
            "questao",
            "questão",
            "exercicio",
            "exercício",
        }
    ):
        return False
    return any(
        pattern in normalized
        for pattern in {
            "pode me ajudar a estudar",
            "pode me ajudar estudar",
            "consegue me ajudar a estudar",
            "consegue me ajudar estudar",
            "me ajuda a estudar",
            "me ajude a estudar",
            "quero estudar",
            "preciso estudar",
        }
    )


def maybe_handle_study_command(user_input: str, show_hud: Callable[[], str]) -> str | None:
    normalized = normalize_text(user_input)

    if _is_general_study_help_request(normalized):
        return None

    file_request = parse_study_file_command(user_input)
    if file_request:
        paths, request = file_request
        if request_is_study_or_practice(request):
            _refresh_study_snapshot(open_panel=False)
        return _block_corrupted_study_response(analyze_study_files(paths, request=request))

    if normalized in {
        "limpar contexto de estudo",
        "limpar arquivo de estudo",
        "esquecer arquivo de estudo",
        "zerar contexto de estudo",
    }:
        clear_study_context()
        _refresh_study_snapshot(open_panel=True)
        return "Contexto do ultimo arquivo de estudo limpo."

    self_test_response = run_study_file_self_test(user_input)
    if self_test_response:
        _refresh_study_snapshot_for_current_file(user_input)
        return polish_study_response(self_test_response)

    followup_response = answer_study_followup(user_input)
    if followup_response:
        _refresh_study_snapshot_for_current_file(user_input)
        return polish_study_response(followup_response)

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
