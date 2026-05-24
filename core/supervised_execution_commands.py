from __future__ import annotations

from core.router_utils import normalize_text
from memory.action_candidates import (
    approve_first_action_candidate,
    load_action_candidates,
    reject_first_action_candidate,
    save_action_candidates,
)
from memory.approval_gate import approve_current_proposal
from memory.codex_implementation_request import save_codex_implementation_request
from memory.execution_packages import load_execution_package, save_execution_package
from memory.handoff_applications import sync_handoff_application
from memory.implementation_handoff import save_implementation_handoff


def maybe_handle_action_candidate_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "gerar acoes candidatas",
        "atualizar acoes candidatas",
        "gerar acoes do axel",
    }:
        items = save_action_candidates()
        if not items:
            return "Ainda nao encontrei acoes candidatas para estruturar."
        top = str(items[0].get("title", "")).strip()
        return f"Atualizei as acoes candidatas do Axel. Primeira acao: {top}."

    if normalized in {
        "acoes candidatas",
        "mostrar acoes candidatas",
        "acoes do axel",
        "qual a proxima acao candidata",
    }:
        items = load_action_candidates()
        if not items:
            return "Ainda nao ha acoes candidatas."
        parts = []
        for index, item in enumerate(items[:3], start=1):
            title = str(item.get("title", "")).strip()
            status = str(item.get("status", "pending")).strip()
            files = item.get("files") or []
            if title:
                files_text = ", ".join(str(file) for file in files[:3])
                parts.append(f"{index}. {title}. Status: {status}. Alvos: {files_text}")
        return "Acoes candidatas: " + "; ".join(parts)

    if normalized in {
        "aprovar acao candidata",
        "aprovar primeira acao",
        "aprovar acao do axel",
    }:
        item = approve_first_action_candidate()
        title = str(item.get("title", "")).strip()
        if not title:
            return "Nao encontrei acao candidata para aprovar."
        return f"Acao candidata aprovada: {title}. Ainda nao executei; deixei pronta para aplicacao supervisionada."

    if normalized in {
        "aprovar proximo avanco",
        "aprovar e preparar proximo avanco",
        "aprovar proximo passo",
        "preparar proximo avanco aprovado",
    }:
        proposal_state = approve_current_proposal("aprovado pelo operador para preparacao supervisionada")
        candidate = approve_first_action_candidate("aprovado pelo operador para preparacao supervisionada")
        package = save_execution_package()
        handoff = save_implementation_handoff()
        sync_handoff_application()
        request = save_codex_implementation_request()

        proposal_title = str((proposal_state.get("proposal") or {}).get("title", "")).strip()
        candidate_title = str(candidate.get("title", "")).strip()
        title = candidate_title or proposal_title
        if not title:
            return "Nao encontrei um proximo avanco para aprovar."

        package_status = str(package.get("status", "")).strip()
        handoff_status = str(handoff.get("status", "")).strip()
        request_status = str(request.get("status", "")).strip()
        return (
            f"Aprovei e preparei o proximo avanco: {title}. "
            f"Pacote: {package_status}; handoff: {handoff_status}; pedido ao Codex: {request_status}."
        )

    if normalized in {
        "rejeitar acao candidata",
        "rejeitar primeira acao",
        "rejeitar acao do axel",
    }:
        item = reject_first_action_candidate()
        title = str(item.get("title", "")).strip()
        if not title:
            return "Nao encontrei acao candidata para rejeitar."
        return f"Acao candidata rejeitada: {title}."

    if normalized in {
        "executar acao candidata",
        "executar primeira acao",
    }:
        return "Ainda nao executo acao candidata sozinho. O caminho seguro e aprovar, levar ao Codex e verificar o resultado."

    return None


def maybe_handle_execution_package_command(user_input: str) -> str | None:
    normalized = normalize_text(user_input)

    if normalized in {
        "gerar pacote de execucao",
        "preparar pacote de execucao",
        "montar pacote de execucao",
        "preparar aplicacao supervisionada",
    }:
        payload = save_execution_package()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        if status == "waiting_for_approval":
            return "Ainda nao ha acao candidata aprovada para montar pacote de execucao."
        return f"Pacote de execucao preparado para o Codex: {title}. Status: {status}."

    if normalized in {
        "pacote de execucao",
        "mostrar pacote de execucao",
        "plano de execucao",
        "mostrar plano de execucao",
    }:
        payload = load_execution_package()
        status = str(payload.get("status", "")).strip()
        title = str(payload.get("title", "")).strip()
        files = payload.get("files") or []
        validation = payload.get("validation") or []
        if status == "waiting_for_approval":
            return "O pacote de execucao ainda aguarda uma acao candidata aprovada."
        files_text = ", ".join(str(file) for file in files[:4])
        validation_text = "; ".join(str(command) for command in validation[:2])
        return f"Pacote de execucao: {title}. Status: {status}. Arquivos: {files_text}. Validacao: {validation_text}."

    if normalized in {
        "executar pacote de execucao",
        "aplicar pacote de execucao",
    }:
        return "Ainda nao aplico o pacote automaticamente. Ele esta pronto para o Codex revisar, editar e validar com voce supervisionando."

    return None
