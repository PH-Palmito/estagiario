import json
import os
import time
from pathlib import Path

from memory.approval_gate import load_approval_gate
from memory.auto_advances import load_auto_advances
from memory.codex_bridge import load_codex_request
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
    codex_decision = latest_codex_inbox_item("decision")
    codex_next_step = latest_codex_inbox_item("next_step")
    current_focus = str(codex_decision.get("text", "")).strip() or str(codex_next_step.get("text", "")).strip()
    if not current_focus:
        current_focus = advances[0]["title"] if advances else "Lapidar a proxima melhoria"
    approval_status = str(approval.get("status", "none")).strip()
    verification_status = str(verification.get("status", "idle")).strip()

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
