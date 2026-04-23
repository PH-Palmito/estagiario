import json
import os
import time
from pathlib import Path

from memory.approval_gate import load_approval_gate
from memory.action_candidates import load_action_candidates
from memory.auto_advances import load_auto_advances
from memory.codex_bridge import load_codex_request
from memory.codex_implementation_request import load_codex_implementation_request
from memory.codex_outbox import load_codex_outbox
from memory.handoff_applications import load_handoff_application
from memory.handoff_retry_plan import load_handoff_retry_plan
from memory.handoff_validation import load_handoff_validation
from memory.codex_inbox import latest_codex_inbox_item
from memory.verification_runs import load_verification_runs


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
SELF_EVOLUTION_PATH = MEMORY_DIR / "self_evolution.json"


def _save_json(path: Path, payload: dict):
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _done_steps() -> set[str]:
    return {
        "hud_runtime_state",
        "auto_advances",
        "codex_bridge",
    }


def generate_self_evolution_plan() -> dict:
    advances = load_auto_advances()
    bridge = load_codex_request()
    approval = load_approval_gate()
    verification = load_verification_runs()
    action_candidates = load_action_candidates()
    handoff_application = load_handoff_application()
    handoff_retry = load_handoff_retry_plan()
    handoff_validation = load_handoff_validation()
    implementation_request = load_codex_implementation_request()
    outbox = load_codex_outbox()
    codex_decision = latest_codex_inbox_item("decision")
    codex_next_step = latest_codex_inbox_item("next_step")
    current_focus = str(codex_decision.get("text", "")).strip() or str(codex_next_step.get("text", "")).strip()
    if not current_focus:
        current_focus = advances[0]["title"] if advances else "Lapidar a proxima melhoria"
    approval_status = str(approval.get("status", "none")).strip()
    verification_status = str(verification.get("status", "idle")).strip()
    application_status = str(handoff_application.get("status", "blocked")).strip()
    handoff_validation_status = str(handoff_validation.get("status", "blocked")).strip()
    handoff_retry_status = str(handoff_retry.get("status", "blocked")).strip()
    implementation_request_status = str(implementation_request.get("status", "blocked")).strip()
    outbox_items = list(outbox.get("pending", [])) + list(outbox.get("sent", []))
    implementation_outbox_status = "planned"
    for item in outbox_items:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind", "")).strip()
        message_key = str(item.get("message_key", "")).strip()
        if kind == "implementation_request" or message_key.startswith("implementation:"):
            implementation_outbox_status = "done" if item in outbox.get("sent", []) else "next"
            break

    steps = [
        {
            "id": "hud_runtime_state",
            "title": "HUD operacional e memoria de uso",
            "status": "done",
            "reason": "O Axel ja acompanha estado, historico, perfil e proximos avancos.",
        },
        {
            "id": "auto_advances",
            "title": "Geracao automatica de proximos avancos",
            "status": "done",
            "reason": "O projeto ja propoe melhorias com base em backlog, perfil e historico recente.",
        },
        {
            "id": "codex_bridge",
            "title": "Pedido estruturado ao Codex",
            "status": "done",
            "reason": "O Axel ja consegue preparar um briefing tecnico para pedir a propria melhoria.",
        },
        {
            "id": "issue_detector",
            "title": "Detector automatico de gargalos e falhas repetidas",
            "status": "done",
            "reason": "O Axel agora consegue observar historico recente e marcar gargalos recorrentes.",
        },
        {
            "id": "safe_patch_proposals",
            "title": "Gerador de propostas de patch com arquivos alvo",
            "status": "done",
            "reason": "O Axel agora consegue transformar gargalos em propostas de patch com arquivos alvo.",
        },
        {
            "id": "approval_gate",
            "title": "Aprovacao humana antes de alterar codigo",
            "status": "done" if approval_status == "approved" else "next",
            "reason": (
                "Ja existe uma proposta aprovada para seguir adiante com seguranca."
                if approval_status == "approved"
                else "Auto-reescrita sem aprovacao nao e segura. O Axel precisa propor, nao impor."
            ),
        },
        {
            "id": "verify_and_retry",
            "title": "Verificacao automatica apos cada melhoria",
            "status": (
                "done"
                if verification_status == "success"
                else "next"
                if approval_status == "approved"
                else "planned"
            ),
            "reason": (
                "A melhoria aprovada ja foi verificada e passou no ciclo de confirmacao."
                if verification_status == "success"
                else "A melhoria aprovada falhou na verificacao e precisa de nova tentativa."
                if verification_status == "failed"
                else "Toda melhoria precisa compilar, testar e comparar efeito antes de ser considerada boa."
            ),
        },
        {
            "id": "action_candidates",
            "title": "Acoes candidatas antes de executar mudancas",
            "status": "done" if action_candidates else "planned",
            "reason": (
                "O Axel ja consegue transformar orientacoes em acoes candidatas com arquivos alvo."
                if action_candidates
                else "O Axel ainda precisa converter decisoes em passos concretos antes de alterar codigo."
            ),
        },
        {
            "id": "handoff_application",
            "title": "Aplicacao supervisionada do handoff",
            "status": (
                "done"
                if application_status == "validated"
                else "next"
                if application_status in {"ready", "in_progress", "applied", "failed"}
                else "planned"
            ),
            "reason": (
                "O handoff foi aplicado e validado pelo operador."
                if application_status == "validated"
                else "O Codex ja aplicou o handoff; falta validar se a melhoria resolveu o problema."
                if application_status == "applied"
                else "O handoff falhou ou ficou incompleto; a proxima tentativa deve usar esse registro."
                if application_status == "failed"
                else "Existe um handoff pronto ou em andamento para o Codex aplicar com supervisao."
                if application_status in {"ready", "in_progress"}
                else "Ainda falta um handoff pronto antes de acompanhar aplicacao real."
            ),
        },
        {
            "id": "codex_implementation_request",
            "title": "Pedido direto para o Codex implementar",
            "status": "done" if implementation_request_status == "ready_for_codex" else "planned",
            "reason": (
                "O Axel ja consegue gerar uma mensagem objetiva para o Codex aplicar o handoff."
                if implementation_request_status == "ready_for_codex"
                else "Quando houver handoff pronto, o Axel deve gerar uma mensagem limpa para implementacao."
            ),
        },
        {
            "id": "codex_implementation_outbox",
            "title": "Fila supervisionada de implementacao para o Codex",
            "status": implementation_outbox_status,
            "reason": (
                "O pedido de implementacao ja foi marcado como entregue ao Codex."
                if implementation_outbox_status == "done"
                else "O pedido de implementacao esta na fila e aguarda entrega ao Codex."
                if implementation_outbox_status == "next"
                else "Depois de gerar o pedido, o Axel ainda precisa coloca-lo na fila supervisionada."
            ),
        },
        {
            "id": "handoff_validation_checklist",
            "title": "Checklist de validacao apos aplicacao",
            "status": (
                "done"
                if application_status == "validated"
                else "next"
                if handoff_validation_status == "ready"
                else "planned"
            ),
            "reason": (
                "A aplicacao ja foi validada pelo operador."
                if application_status == "validated"
                else "O Axel ja tem um roteiro objetivo para validar a melhoria aplicada."
                if handoff_validation_status == "ready"
                else "Quando o Codex aplicar o handoff, o Axel deve guiar a validacao no uso real."
            ),
        },
        {
            "id": "handoff_retry_plan",
            "title": "Plano de nova tentativa apos falha",
            "status": (
                "done"
                if application_status == "validated"
                else "next"
                if handoff_retry_status == "ready_for_codex"
                else "planned"
            ),
            "reason": (
                "A melhoria foi validada, entao nao precisa de nova tentativa agora."
                if application_status == "validated"
                else "O Axel ja consegue transformar a falha em um novo plano para o Codex."
                if handoff_retry_status == "ready_for_codex"
                else "Se a validacao falhar, o Axel deve gerar uma nova tentativa com evidencias."
            ),
        },
    ]

    payload = {
        "generated_at": time.time(),
        "goal": "Permitir que o Axel evolua o proprio projeto com supervisao e seguranca.",
        "current_focus": current_focus,
        "codex_request_title": bridge.get("title", ""),
        "steps": steps,
    }
    return payload


def save_self_evolution_plan() -> dict:
    payload = generate_self_evolution_plan()
    _save_json(SELF_EVOLUTION_PATH, payload)
    return payload


def load_self_evolution_plan() -> dict:
    if not SELF_EVOLUTION_PATH.exists():
        return save_self_evolution_plan()

    try:
        data = json.loads(SELF_EVOLUTION_PATH.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("steps"):
            return data
    except Exception:
        pass
    return save_self_evolution_plan()
