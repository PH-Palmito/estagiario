from __future__ import annotations

from core.router_utils import normalize_text
from memory.approval_gate import approve_current_proposal, load_approval_gate, reject_current_proposal
from memory.auto_advances import save_auto_advances
from memory.codex_bridge import save_codex_request
from memory.patch_proposals import save_patch_proposals
from memory.verification_runs import (
    load_verification_runs,
    mark_verification_failed,
    mark_verification_success,
    retry_verification,
    start_verification,
)


def maybe_handle_approval_gate_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "mostrar proposta atual",
        "proposta atual",
        "qual a proposta atual",
        "status da proposta",
    }:
        state = load_approval_gate()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        files = proposal.get("files") or []
        status = str(state.get("status", "none")).strip()
        if not title:
            return "Nao ha proposta atual para aprovar."
        files_text = ", ".join(str(file) for file in files[:4]) if files else "sem arquivos alvo definidos"
        return f"Proposta atual: {title}. Status: {status}. Arquivos alvo: {files_text}."

    if normalized in {
        "aprovar proposta",
        "aprovar proposta atual",
        "aprovar proposta de patch",
    }:
        state = approve_current_proposal()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if title:
            return f"Proposta aprovada. O Axel pode levar ao Codex esta melhoria: {title}."
        return "Proposta aprovada."

    if normalized in {
        "rejeitar proposta",
        "rejeitar proposta atual",
        "rejeitar proposta de patch",
    }:
        state = reject_current_proposal()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if title:
            return f"Proposta rejeitada. Vou aguardar uma nova sugestao para substituir: {title}."
        return "Proposta rejeitada."

    return None


def maybe_handle_verification_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "status da verificacao",
        "mostrar verificacao",
        "status da melhoria",
        "como esta a verificacao",
        "verificacao atual",
    }:
        state = load_verification_runs()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        status = str(state.get("status", "idle")).strip()
        attempts = int(state.get("attempts", 0) or 0)
        note = str(state.get("last_note", "")).strip()
        if not title:
            return "Ainda nao ha melhoria aprovada aguardando verificacao."
        base = f"Verificacao atual: {status}. Alvo: {title}. Tentativas: {attempts}."
        if note:
            base += f" Observacao: {note}."
        return base

    if normalized in {
        "verificar melhoria",
        "iniciar verificacao",
        "comecar verificacao",
        "verificar proposta",
    }:
        state = start_verification()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if not title or str(state.get("approval_status", "none")).strip() != "approved":
            return "Ainda nao ha uma proposta aprovada para verificar."
        checklist = state.get("checklist") or []
        checklist_text = "; ".join(str(item) for item in checklist[:3])
        return f"Verificacao iniciada para {title}. Checklist: {checklist_text}."

    if normalized in {
        "melhoria funcionou",
        "verificacao passou",
        "deu certo",
        "funcionou",
        "passou na verificacao",
    }:
        state = mark_verification_success()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if not title:
            return "Nao encontrei uma melhoria aprovada para marcar como sucesso."
        return f"Perfeito. Registrei que a melhoria passou na verificacao: {title}."

    if normalized in {
        "melhoria falhou",
        "verificacao falhou",
        "nao funcionou",
        "falhou",
        "deu errado",
    }:
        state = mark_verification_failed()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if not title:
            return "Nao encontrei uma melhoria aprovada para marcar como falha."
        return f"Registrei falha na verificacao da melhoria: {title}. O Axel deve preparar nova tentativa."

    if normalized in {
        "tentar novamente",
        "nova tentativa",
        "retestar melhoria",
        "verificar de novo",
    }:
        state = retry_verification()
        proposal = state.get("proposal") or {}
        title = str(proposal.get("title", "")).strip()
        if not title:
            return "Ainda nao ha uma melhoria aprovada para tentar de novo."
        return f"Nova tentativa de verificacao iniciada para {title}."

    if normalized in {
        "aprender da falha",
        "replanejar melhoria",
        "gerar nova proposta apos falha",
        "corrigir falha da melhoria",
    }:
        state = load_verification_runs()
        title = str((state.get("proposal") or {}).get("title", "")).strip()
        status = str(state.get("status", "idle")).strip()
        if status != "failed" or not title:
            return "Ainda nao ha uma falha de verificacao forte o suficiente para replanejar."
        save_patch_proposals()
        save_auto_advances()
        save_codex_request()
        return f"Perfeito. O Axel replanejou a melhoria apos a falha de verificacao em {title}."

    return None
