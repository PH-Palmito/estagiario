import json
import os
import time
from pathlib import Path

from memory.approval_gate import load_approval_gate
from memory.codex_bridge import load_codex_request
from memory.codex_inbox import latest_codex_inbox_item
from memory.patch_proposals import load_patch_proposals
from memory.verification_runs import load_verification_runs


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
CODEX_CHANNEL_PATH = MEMORY_DIR / "codex_channel.json"


def _save_json(path: Path, payload: dict):
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _message_key(title: str, trigger: str, status: str) -> str:
    return f"{title.strip().lower()}|{trigger.strip().lower()}|{status.strip().lower()}"


def generate_codex_channel() -> dict:
    bridge = load_codex_request()
    approval = load_approval_gate()
    verification = load_verification_runs()
    proposals = load_patch_proposals()
    codex_decision = latest_codex_inbox_item("decision")
    codex_next_step = latest_codex_inbox_item("next_step")

    title = str(bridge.get("title", "")).strip() or "Melhoria sugerida para o Axel"
    prompt = str(bridge.get("prompt", "")).strip()
    approval_status = str(approval.get("status", "none")).strip()
    verification_status = str(verification.get("status", "idle")).strip()
    verification_note = str(verification.get("last_note", "")).strip()
    top_patch = proposals[0] if proposals else {}
    top_patch_title = str(top_patch.get("title", "")).strip()
    codex_decision_text = str(codex_decision.get("text", "")).strip()
    codex_next_step_text = str(codex_next_step.get("text", "")).strip()

    trigger = "manual_bridge"
    urgency = "normal"
    status = "draft"
    next_action = "Aguardar aprovacao humana antes de pedir alteracao de codigo."
    message = prompt
    should_notify = False
    notify_reason = "Ainda nao ha um momento forte para acionar o Codex."

    if approval_status == "approved" and verification_status in {"idle", "pending"}:
        trigger = "approved_change_ready"
        urgency = "high"
        status = "ready"
        next_action = "Levar a proposta aprovada ao Codex para implementacao guiada."
        should_notify = True
        notify_reason = "Ja existe uma proposta aprovada pronta para implementacao."
        message = (
            f"Axel para Codex: a proposta '{title}' foi aprovada e esta pronta para implementacao. "
            f"Patch sugerido agora: {top_patch_title or title}. "
            f"Use o contexto abaixo como base de trabalho.\n\n{prompt}"
        )
    elif approval_status == "approved" and verification_status == "failed":
        trigger = "verification_failed"
        urgency = "critical"
        status = "ready"
        next_action = "Pedir ao Codex uma nova rodada mais cirurgica com base na falha da verificacao."
        should_notify = True
        notify_reason = "A ultima melhoria aprovada falhou e precisa de nova rodada com prioridade alta."
        extra = f" Observacao da falha: {verification_note}." if verification_note else ""
        message = (
            f"Axel para Codex: a melhoria aprovada '{title}' falhou na verificacao.{extra} "
            f"Nova proposta prioritaria: {top_patch_title or title}. "
            f"Refaça a abordagem com foco no aprendizado da tentativa anterior.\n\n{prompt}"
        )
    elif approval_status == "rejected":
        trigger = "proposal_rejected"
        urgency = "low"
        status = "blocked"
        next_action = "Replanejar antes de acionar o Codex novamente."
        message = (
            f"Axel para Codex: a proposta '{title}' foi rejeitada. "
            "Nao abra uma nova implementacao ainda; primeiro refine a proposta com base no feedback humano."
        )
    elif codex_decision_text or codex_next_step_text:
        trigger = "codex_guidance_available"
        urgency = "normal"
        status = "guided"
        next_action = codex_next_step_text or codex_decision_text
        notify_reason = "Existe uma orientacao recente do Codex que o Axel pode seguir agora."

    payload = {
        "generated_at": time.time(),
        "title": title,
        "trigger": trigger,
        "urgency": urgency,
        "status": status,
        "approval_status": approval_status,
        "verification_status": verification_status,
        "top_patch_title": top_patch_title,
        "codex_decision": codex_decision_text,
        "codex_next_step": codex_next_step_text,
        "next_action": next_action,
        "should_notify": should_notify,
        "notify_reason": notify_reason,
        "message": message,
        "message_key": _message_key(title, trigger, status),
    }
    return payload


def save_codex_channel() -> dict:
    payload = generate_codex_channel()
    existing = _load_json(CODEX_CHANNEL_PATH)
    history = existing.get("history") if isinstance(existing, dict) else None
    history = history if isinstance(history, list) else []

    key = payload["message_key"]
    if not any(str(item.get("message_key", "")).strip() == key for item in history if isinstance(item, dict)):
        history.append(
            {
                "message_key": key,
                "title": payload["title"],
                "trigger": payload["trigger"],
                "status": payload["status"],
                "urgency": payload["urgency"],
                "at": payload["generated_at"],
            }
        )

    payload["history"] = history[-12:]
    _save_json(CODEX_CHANNEL_PATH, payload)
    return payload


def load_codex_channel() -> dict:
    data = _load_json(CODEX_CHANNEL_PATH)
    if isinstance(data, dict) and data.get("message"):
        return data
    return save_codex_channel()
