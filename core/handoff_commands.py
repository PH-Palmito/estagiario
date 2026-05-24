from __future__ import annotations

from core.router_utils import normalize_text
from memory.codex_implementation_request import save_codex_implementation_request
from memory.handoff_applications import (
    load_handoff_application,
    mark_handoff_applied,
    mark_handoff_failed,
    mark_handoff_started,
    mark_handoff_validated,
)
from memory.handoff_retry_plan import load_handoff_retry_plan, save_handoff_retry_plan
from memory.handoff_validation import load_handoff_validation, save_handoff_validation
from memory.implementation_handoff import load_implementation_handoff, save_implementation_handoff
from memory.verification_runs import mark_verification_failed, mark_verification_success, start_verification


def maybe_handle_implementation_handoff_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "gerar handoff",
        "preparar handoff",
        "handoff para codex",
        "gerar handoff para codex",
        "preparar implementacao",
    }:
        payload = save_implementation_handoff()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        if status == "blocked":
            return "Ainda nao ha pacote aprovado pronto para gerar handoff ao Codex."
        return f"Handoff preparado para o Codex: {title}. Status: {status}."

    if normalized in {
        "mostrar handoff",
        "handoff",
        "handoff do codex",
        "handoff do axel",
    }:
        payload = load_implementation_handoff()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        files = payload.get("files") or []
        validation = payload.get("validation") or []
        if status == "blocked":
            return "O handoff ainda esta bloqueado. Primeiro aprove uma acao candidata e gere o pacote de execucao."
        files_text = ", ".join(str(file) for file in files[:4])
        validation_text = "; ".join(str(command) for command in validation[:2])
        return f"Handoff do Axel para o Codex: {title}. Arquivos: {files_text}. Validacao: {validation_text}."

    if normalized in {
        "aplicar handoff",
        "executar handoff",
    }:
        return "Ainda nao aplico o handoff automaticamente. Ele serve para o Codex implementar com supervisao e validacao."

    return None


def maybe_handle_handoff_application_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "status da aplicacao",
        "status da aplicacao do handoff",
        "aplicacao do handoff",
        "mostrar aplicacao",
    }:
        state = load_handoff_application()
        status = str(state.get("status", "blocked")).strip()
        handoff = state.get("handoff") or {}
        title = str(handoff.get("title", "")).strip()
        note = str(state.get("last_note", "")).strip()
        if not title:
            return f"Aplicacao do handoff: {status}. Ainda nao ha handoff pronto."
        response = f"Aplicacao do handoff: {status}. Alvo: {title}."
        if note:
            response += f" Nota: {note}."
        return response

    if normalized in {
        "iniciar aplicacao do handoff",
        "marcar handoff em andamento",
        "codex comecou handoff",
    }:
        state = mark_handoff_started()
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if state.get("status") == "blocked" or not title:
            return "Ainda nao ha handoff pronto para marcar como em andamento."
        return f"Registrei aplicacao em andamento para: {title}."

    if normalized in {
        "handoff aplicado",
        "codex aplicou handoff",
        "marcar handoff aplicado",
        "implementacao aplicada",
    }:
        state = mark_handoff_applied()
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if state.get("status") == "blocked" or not title:
            return "Ainda nao ha handoff pronto para marcar como aplicado."
        verification = start_verification("handoff aplicado; aguardando validacao")
        if verification.get("status") == "pending":
            return f"Registrei o handoff como aplicado: {title}. Iniciei a verificacao da melhoria."
        return f"Registrei o handoff como aplicado: {title}. Aguardando validacao supervisionada."

    if normalized in {
        "handoff falhou",
        "codex falhou handoff",
        "marcar handoff falhou",
        "implementacao falhou",
    }:
        state = mark_handoff_failed()
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if state.get("status") == "blocked" or not title:
            return "Ainda nao ha handoff pronto para marcar como falha."
        verification = mark_verification_failed("handoff falhou durante aplicacao supervisionada")
        if verification.get("status") == "failed":
            return f"Registrei falha na aplicacao do handoff: {title}. Isso vai alimentar uma nova tentativa."
        return f"Registrei falha na aplicacao do handoff: {title}. O rastreador do handoff vai alimentar uma nova tentativa."

    if normalized in {
        "handoff validado",
        "aplicacao validada",
        "aplicacao funcionou",
        "implementacao validada",
        "melhoria aplicada funcionou",
    }:
        state = mark_handoff_validated("validado pelo operador")
        title = str((state.get("handoff") or {}).get("title", "")).strip()
        if state.get("status") == "blocked" or not title:
            return "Ainda nao ha handoff pronto para marcar como validado."
        mark_verification_success("handoff validado pelo operador")
        return f"Excelente. Marquei o handoff como validado: {title}."

    return None


def maybe_handle_handoff_validation_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "como validar handoff",
        "validar handoff",
        "checklist do handoff",
        "checklist de validacao",
        "validacao do handoff",
        "validacao da aplicacao",
    }:
        payload = save_handoff_validation()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        checklist = payload.get("checklist") or []
        if status == "blocked":
            return "Ainda nao ha handoff aplicado para validar."
        summary = "; ".join(str(item) for item in checklist[:4])
        return f"Checklist para validar {title}: {summary}."

    if normalized in {
        "mostrar checklist do handoff",
        "mostrar validacao do handoff",
        "mostrar roteiro de validacao",
    }:
        payload = load_handoff_validation()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        checklist = payload.get("checklist") or []
        if status == "blocked":
            return "O roteiro de validacao ainda esta bloqueado. Primeiro o Codex precisa aplicar o handoff."
        summary = "; ".join(str(item) for item in checklist[:6])
        return f"Roteiro de validacao para {title}: {summary}."

    return None


def maybe_handle_handoff_retry_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "plano de nova tentativa",
        "nova tentativa do handoff",
        "replanejar handoff",
        "corrigir handoff",
        "preparar nova tentativa",
        "preparar nova tentativa para codex",
    }:
        payload = save_handoff_retry_plan()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        evidence = payload.get("evidence") or []
        if status == "blocked":
            return "Ainda nao ha uma falha de handoff forte o suficiente para montar nova tentativa."
        request = save_codex_implementation_request()
        clue = str(evidence[0]) if evidence else "falha registrada no handoff"
        if request.get("source") == "handoff_retry_plan":
            return f"Plano de nova tentativa pronto para o Codex: {title}. Principal pista: {clue}."
        return f"Plano de nova tentativa pronto: {title}. Principal pista: {clue}."

    if normalized in {
        "mostrar plano de nova tentativa",
        "mostrar tentativa do handoff",
        "mostrar replanejamento do handoff",
    }:
        payload = load_handoff_retry_plan()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        steps = payload.get("steps") or []
        if status == "blocked":
            return "O plano de nova tentativa ainda esta bloqueado. Primeiro registre uma falha do handoff."
        summary = "; ".join(str(item) for item in steps[:4])
        return f"Nova tentativa para {title}: {summary}."

    return None
