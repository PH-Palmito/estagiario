import json
import os
import time
from pathlib import Path

from memory.approval_gate import load_approval_gate
from memory.auto_advances import load_auto_advances
from memory.bottlenecks import load_bottlenecks
from memory.codex_inbox import latest_codex_inbox_item
from memory.patch_proposals import load_patch_proposals
from memory.verification_runs import load_verification_runs


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
PROFILE_PATH = MEMORY_DIR / "profile.json"
UI_STATE_PATH = MEMORY_DIR / "ui_state.json"
CODEX_BRIDGE_PATH = MEMORY_DIR / "codex_bridge.json"
CODEX_BRIDGE_MD_PATH = MEMORY_DIR / "codex_bridge.md"


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_json(path: Path, payload: dict):
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _profile_context() -> dict:
    data = _load_json(PROFILE_PATH)
    return data if isinstance(data, dict) else {}


def _ui_context() -> dict:
    data = _load_json(UI_STATE_PATH)
    return data if isinstance(data, dict) else {}


def _history_lines(limit: int = 8) -> list[str]:
    state = _ui_context()
    history = state.get("history") or []
    lines = []
    if not isinstance(history, list):
        return lines
    for item in history[-limit:]:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role", "system")).strip().upper()
        label = "Usuario" if role == "USER" else "Axel" if role == "ASSISTANT" else role.title()
        text = str(item.get("text", "")).strip()
        if text:
            lines.append(f"{label}: {text}")
    return lines


def generate_codex_request() -> dict:
    profile = _profile_context()
    ui = _ui_context()
    advances = load_auto_advances()
    bottlenecks = load_bottlenecks()
    proposals = load_patch_proposals()
    approval = load_approval_gate()
    verification = load_verification_runs()
    codex_decision = latest_codex_inbox_item("decision")
    codex_next_step = latest_codex_inbox_item("next_step")
    top = advances[0] if advances else {}

    operator = str(profile.get("nome", "Pedro Henrique")).strip() or "Pedro Henrique"
    focus = ", ".join(str(item) for item in profile.get("foco_profissional", [])[:4]) or "desenvolvimento de software"
    assistant_name = str(ui.get("assistant_name", "Axel")).strip() or "Axel"
    last_heard = str(ui.get("last_heard", "")).strip()
    last_response = str(ui.get("last_response", "")).strip()
    recent_history = _history_lines()

    title = top.get("title") or "Melhoria sugerida para o Axel"
    reason = top.get("reason") or "Ainda nao ha uma justificativa detalhada."
    source = top.get("source") or "heuristica"

    prompt_lines = [
        f"O assistente local se chama {assistant_name}.",
        f"O operador principal e {operator}, com foco em {focus}.",
        f"Melhoria sugerida agora: {title}.",
        f"Motivo: {reason}",
        f"Origem da sugestao: {source}.",
    ]
    if last_heard:
        prompt_lines.append(f"Ultima fala relevante do usuario: {last_heard}.")
    if last_response:
        prompt_lines.append(f"Ultima resposta do assistente: {last_response}.")
    if recent_history:
        prompt_lines.append("Historico recente:")
        prompt_lines.extend(recent_history[:6])

    if bottlenecks:
        prompt_lines.append("Gargalos detectados recentemente:")
        for item in bottlenecks[:3]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            count = int(item.get("count", 0) or 0)
            if title:
                prompt_lines.append(f"- {title} ({count} ocorrencia(s))")

    if proposals:
        prompt_lines.append("Propostas iniciais de patch:")
        for item in proposals[:2]:
            if not isinstance(item, dict):
                continue
            title = str(item.get("title", "")).strip()
            files = item.get("files") or []
            if title:
                prompt_lines.append(f"- {title} | arquivos: {', '.join(str(file) for file in files[:4])}")

    approval_status = str(approval.get("status", "none")).strip()
    approval_proposal = approval.get("proposal") or {}
    approval_title = str(approval_proposal.get("title", "")).strip()
    if approval_title:
        prompt_lines.append(f"Status da aprovacao humana: {approval_status}.")
        prompt_lines.append(f"Proposta em revisao: {approval_title}.")

    verification_status = str(verification.get("status", "idle")).strip()
    verification_note = str(verification.get("last_note", "")).strip()
    if approval_title:
        prompt_lines.append(f"Status da verificacao da melhoria: {verification_status}.")
    if verification_note:
        prompt_lines.append(f"Observacao da verificacao: {verification_note}.")

    decision_text = str(codex_decision.get("text", "")).strip()
    next_step_text = str(codex_next_step.get("text", "")).strip()
    if decision_text:
        prompt_lines.append(f"Ultima decisao registrada do Codex: {decision_text}.")
    if next_step_text:
        prompt_lines.append(f"Ultimo proximo passo sugerido pelo Codex: {next_step_text}.")

    prompt_lines.append("Quero que o Codex use isso como briefing para melhorar o Axel com seguranca e impacto pratico.")

    return {
        "generated_at": time.time(),
        "assistant_name": assistant_name,
        "title": title,
        "reason": reason,
        "source": source,
        "prompt": "\n".join(prompt_lines),
        "history": recent_history,
    }


def save_codex_request() -> dict:
    payload = generate_codex_request()
    _save_json(CODEX_BRIDGE_PATH, payload)
    markdown = [
        "# Pedido do Axel ao Codex",
        "",
        f"**Assistente:** {payload.get('assistant_name', 'Axel')}",
        f"**Foco atual:** {payload.get('title', '')}",
        "",
        "## Contexto",
        payload.get("prompt", ""),
        "",
    ]
    CODEX_BRIDGE_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")
    return payload


def load_codex_request() -> dict:
    data = _load_json(CODEX_BRIDGE_PATH)
    if isinstance(data, dict) and data.get("prompt"):
        return data
    return save_codex_request()
