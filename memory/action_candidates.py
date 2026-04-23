import json
import os
import time
from pathlib import Path

from memory.codex_inbox import latest_codex_inbox_item
from memory.patch_proposals import load_patch_proposals


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
ACTION_CANDIDATES_PATH = MEMORY_DIR / "action_candidates.json"


def _save_json(path: Path, payload: dict):
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    tmp_path = path.with_name(f"{path.stem}.{time.time_ns()}.tmp")
    tmp_path.write_text(content, encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _candidate_key(candidate: dict) -> str:
    title = str(candidate.get("title", "")).strip().lower()
    files = ",".join(str(item) for item in candidate.get("files", []))
    return f"{title}|{files}"


def _files_from_guidance(text: str, fallback: list[str]) -> list[str]:
    normalized = str(text or "").lower()
    if any(word in normalized for word in {"voz", "comando", "classificador", "fala", "whisper"}):
        return [
            "main.py",
            "core/voice_command_classifier.py",
            "memory/voice_corrections.py",
            "voice/windows_voice.py",
        ]
    if any(word in normalized for word in {"interface", "hud", "painel", "visual"}):
        return ["ui/assistant_hud.py", "memory/ui_state.py"]
    if any(word in normalized for word in {"codex", "ponte", "inbox", "outbox", "canal"}):
        return [
            "main.py",
            "memory/codex_channel.py",
            "memory/codex_outbox.py",
            "memory/codex_inbox.py",
        ]
    return list(fallback or ["main.py"])


def generate_action_candidates(limit: int = 4) -> list[dict]:
    proposals = load_patch_proposals()
    top_proposal = proposals[0] if proposals else {}
    decision = latest_codex_inbox_item("decision")
    next_step = latest_codex_inbox_item("next_step")

    decision_text = str(decision.get("text", "")).strip()
    next_step_text = str(next_step.get("text", "")).strip()
    proposal_title = str(top_proposal.get("title", "")).strip()
    proposal_files = list(top_proposal.get("files", []))
    proposal_changes = list(top_proposal.get("changes", []))

    candidates = []
    guidance = next_step_text or decision_text
    if guidance:
        files = _files_from_guidance(guidance, proposal_files)
        candidates.append(
            {
                "title": f"Aplicar orientacao do Codex: {guidance[:84]}",
                "kind": "codex_guided_patch",
                "status": "pending",
                "risk": "Medio. Requer revisao humana antes de alterar codigo.",
                "files": files,
                "steps": [
                    "Localizar os pontos exatos relacionados a orientacao do Codex.",
                    "Preparar patch pequeno e reversivel.",
                    "Compilar e validar o fluxo afetado.",
                ],
                "source": "codex-inbox",
            }
        )

    if proposal_title:
        candidates.append(
            {
                "title": f"Executar proposta de patch: {proposal_title}",
                "kind": "patch_proposal",
                "status": "pending",
                "risk": str(top_proposal.get("risk", "Medio.")).strip(),
                "files": proposal_files or ["main.py"],
                "steps": proposal_changes
                or [
                    "Inspecionar arquivos alvo.",
                    "Aplicar melhoria incremental.",
                    "Validar com py_compile e teste manual do fluxo.",
                ],
                "source": "patch-proposals",
            }
        )

    if not candidates:
        candidates.append(
            {
                "title": "Inspecionar proximo gargalo do Axel",
                "kind": "general_inspection",
                "status": "pending",
                "risk": "Baixo.",
                "files": ["main.py", "memory/auto_advances.py"],
                "steps": [
                    "Ler historico recente.",
                    "Identificar gargalo mais frequente.",
                    "Gerar uma proposta especifica antes de editar.",
                ],
                "source": "fallback",
            }
        )

    return candidates[: max(1, int(limit))]


def save_action_candidates(limit: int = 4) -> list[dict]:
    old = _load_json(ACTION_CANDIDATES_PATH)
    old_items = old.get("items") if isinstance(old, dict) else []
    old_items = old_items if isinstance(old_items, list) else []
    old_status = {
        _candidate_key(item): str(item.get("status", "pending")).strip()
        for item in old_items
        if isinstance(item, dict)
    }

    items = generate_action_candidates(limit=limit)
    for item in items:
        key = _candidate_key(item)
        if key in old_status:
            item["status"] = old_status[key]

    payload = {
        "generated_at": time.time(),
        "items": items,
    }
    _save_json(ACTION_CANDIDATES_PATH, payload)
    return items


def load_action_candidates() -> list[dict]:
    data = _load_json(ACTION_CANDIDATES_PATH)
    items = data.get("items") if isinstance(data, dict) else None
    if isinstance(items, list) and items:
        return items
    return save_action_candidates()


def approve_first_action_candidate(note: str = "") -> dict:
    items = load_action_candidates()
    if not items:
        return {}
    items[0]["status"] = "approved"
    items[0]["decision_note"] = str(note or "").strip()
    items[0]["decided_at"] = time.time()
    _save_json(ACTION_CANDIDATES_PATH, {"generated_at": time.time(), "items": items})
    return items[0]


def reject_first_action_candidate(note: str = "") -> dict:
    items = load_action_candidates()
    if not items:
        return {}
    items[0]["status"] = "rejected"
    items[0]["decision_note"] = str(note or "").strip()
    items[0]["decided_at"] = time.time()
    _save_json(ACTION_CANDIDATES_PATH, {"generated_at": time.time(), "items": items})
    return items[0]
