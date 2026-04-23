import json
import os
import time
from pathlib import Path

from memory.bottlenecks import load_bottlenecks
from memory.codex_inbox import latest_codex_inbox_item
from memory.verification_runs import load_verification_runs


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
TODO_PATH = MEMORY_DIR / "todo.md"
PROFILE_PATH = MEMORY_DIR / "profile.json"
UI_STATE_PATH = MEMORY_DIR / "ui_state.json"
AUTO_ADVANCES_PATH = MEMORY_DIR / "auto_advances.json"


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_profile() -> dict:
    data = _load_json(PROFILE_PATH)
    return data if isinstance(data, dict) else {}


def _load_ui_state() -> dict:
    data = _load_json(UI_STATE_PATH)
    return data if isinstance(data, dict) else {}


def _load_manual_pending() -> list[str]:
    try:
        lines = TODO_PATH.read_text(encoding="utf-8").splitlines()
    except Exception:
        return []

    pending = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- [ ] "):
            pending.append(stripped[6:].strip())
    return pending


def _recent_history_text() -> str:
    state = _load_ui_state()
    history = state.get("history") or []
    if not isinstance(history, list):
        return ""
    parts = []
    for item in history[-12:]:
        if isinstance(item, dict):
            parts.append(str(item.get("text", "")))
    return " ".join(parts).lower()


def _push(items: list[dict], title: str, reason: str, source: str):
    normalized = title.strip().lower()
    if any(item.get("title", "").strip().lower() == normalized for item in items):
        return
    items.append({
        "title": title.strip(),
        "reason": reason.strip(),
        "source": source.strip(),
    })


def generate_auto_advances(limit: int = 6) -> list[dict]:
    profile = _load_profile()
    pending = _load_manual_pending()
    recent = _recent_history_text()
    bottlenecks = load_bottlenecks()
    verification = load_verification_runs()
    codex_decision = latest_codex_inbox_item("decision")
    codex_next_step = latest_codex_inbox_item("next_step")
    items: list[dict] = []

    decision_text = str(codex_decision.get("text", "")).strip()
    next_step_text = str(codex_next_step.get("text", "")).strip()

    if decision_text:
        _push(
            items,
            f"Executar decisao do Codex: {decision_text[:72]}",
            "O Codex ja deixou uma decisao registrada na inbox do Axel e isso deve influenciar o proximo movimento do projeto.",
            "codex-inbox",
        )
    elif next_step_text:
        _push(
            items,
            f"Seguir proximo passo do Codex: {next_step_text[:72]}",
            "O Codex ja sugeriu um proximo passo concreto e o Axel pode usar isso para priorizar a trilha de melhoria.",
            "codex-inbox",
        )

    verification_status = str(verification.get("status", "idle")).strip()
    verification_proposal = verification.get("proposal") or {}
    verification_title = str(verification_proposal.get("title", "")).strip()
    verification_note = str(verification.get("last_note", "")).strip()

    if verification_status == "failed" and verification_title:
        reason = f"A ultima melhoria aprovada falhou na verificacao: {verification_title}."
        if verification_note:
            reason += f" Observacao registrada: {verification_note}."
        _push(
            items,
            f"Corrigir falha na melhoria aprovada: {verification_title}",
            reason,
            "verificacao",
        )

    for bottleneck in bottlenecks[:2]:
        if not isinstance(bottleneck, dict):
            continue
        title = str(bottleneck.get("title", "")).strip()
        count = int(bottleneck.get("count", 0) or 0)
        if title:
            _push(
                items,
                f"Resolver gargalo: {title}",
                f"O detector automatico marcou esse problema {count} vez(es) no uso recente.",
                "detector-de-gargalos",
            )

    if "modo de auto avanco" in " ".join(pending).lower():
        _push(
            items,
            "Criar um planejador de auto-avanco com prioridade",
            "O proprio backlog ja pede um modo em que o Axel proponha melhorias ao Codex com mais criterio.",
            "lista-manual",
        )

    if "ditado" in recent or "modo ditado" in recent:
        _push(
            items,
            "Integrar ditado ao HUD com indicador dedicado",
            "Voce ja usa voz com frequencia; juntar ditado e painel deve reduzir atrito no uso diario.",
            "historico-recente",
        )

    if any(word in recent for word in {"tela", "github", "resuma", "detalha", "conteudo principal"}):
        _push(
            items,
            "Aprimorar leitura util de pagina com foco no conteudo central",
            "Seu uso recente mostra bastante navegacao orientada por tela; vale melhorar relevancia, resumo e clique contextual.",
            "historico-recente",
        )

    if any(word in pending_text.lower() for pending_text in pending for word in {"imagem", "analisar imagens"}):
        _push(
            items,
            "Adicionar analise de imagens ao fluxo do Axel",
            "A lista manual ja aponta isso, e a interface pode virar a base visual para esse passo.",
            "lista-manual",
        )

    if any(word in pending_text.lower() for pending_text in pending for word in {"erros em codigos", "codigos"}):
        _push(
            items,
            "Criar um modo de inspecao de codigo com busca de erros",
            "Voce trabalha com sistemas completos e esse ganho conversa diretamente com seu uso de projetos reais.",
            "lista-manual",
        )

    if profile.get("assistente", {}).get("nome") == "Axel":
        _push(
            items,
            "Dar ao Axel memoria operacional de preferencias e contexto",
            "O projeto ja tem perfil, voz e HUD; o proximo passo natural e usar isso para respostas e sugestoes mais contextualizadas.",
            "perfil",
        )

    foco = " ".join(str(item) for item in profile.get("foco_profissional", []))
    if any(word in foco.lower() for word in {"mobile", "react native", "front-end"}):
        _push(
            items,
            "Criar rotinas prontas para estudo e desenvolvimento mobile/front-end",
            "Seu perfil tecnico pede fluxos de abertura de projeto, navegador, docs e debug com menos atrito.",
            "perfil",
        )

    if "fazer o axel iniciar junto com o windows" in " ".join(pending).lower():
        _push(
            items,
            "Preparar inicializacao automatica com Windows",
            "Isso transforma o Axel de projeto em ferramenta do dia a dia.",
            "lista-manual",
        )

    if not items:
        _push(
            items,
            "Lapidar robustez de voz e comandos compostos",
            "Mesmo quando tudo funciona, melhorar entendimento de comando continua sendo o ganho com melhor retorno.",
            "fallback",
        )

    return items[: max(1, int(limit))]


def save_auto_advances(limit: int = 6) -> list[dict]:
    advances = generate_auto_advances(limit=limit)
    payload = {
        "generated_at": time.time(),
        "items": advances,
    }
    tmp_path = AUTO_ADVANCES_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, AUTO_ADVANCES_PATH)
    return advances


def load_auto_advances() -> list[dict]:
    data = _load_json(AUTO_ADVANCES_PATH)
    items = data.get("items") if isinstance(data, dict) else None
    if isinstance(items, list) and items:
        return items
    return save_auto_advances()
