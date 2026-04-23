import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
APPROVAL_GATE_PATH = MEMORY_DIR / "approval_gate.json"
VERIFICATION_RUNS_PATH = MEMORY_DIR / "verification_runs.json"


def _save_json(path: Path, payload: dict):
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp_path, path)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _proposal_key(proposal: dict) -> str:
    title = str(proposal.get("title", "")).strip().lower()
    files = ",".join(str(item) for item in proposal.get("files", []))
    return f"{title}|{files}"


def _load_approval_gate() -> dict:
    data = _load_json(APPROVAL_GATE_PATH)
    return data if isinstance(data, dict) else {}


def _default_state() -> dict:
    approval = _load_approval_gate()
    proposal = approval.get("proposal") or {}
    status = "pending" if approval.get("status") == "approved" and proposal else "idle"
    return {
        "generated_at": time.time(),
        "status": status,
        "proposal_key": _proposal_key(proposal) if proposal else "",
        "proposal": proposal,
        "approval_status": str(approval.get("status", "none")).strip(),
        "last_result": "",
        "last_note": "",
        "last_checked_at": 0.0,
        "attempts": 0,
        "checklist": [
            "Compilar ou carregar os arquivos alterados sem erro.",
            "Validar o fluxo principal relacionado ao gargalo.",
            "Comparar se o gargalo realmente diminuiu no uso.",
        ],
    }


def sync_verification_runs() -> dict:
    current_state = _load_json(VERIFICATION_RUNS_PATH)
    if not isinstance(current_state, dict) or "status" not in current_state:
        current_state = _default_state()

    approval = _load_approval_gate()
    approval_status = str(approval.get("status", "none")).strip()
    proposal = approval.get("proposal") or {}
    proposal_key = _proposal_key(proposal) if proposal else ""

    old_key = str(current_state.get("proposal_key", "")).strip()
    old_approval = str(current_state.get("approval_status", "none")).strip()

    if proposal_key != old_key or approval_status != old_approval:
        current_state = _default_state()
    else:
        current_state["approval_status"] = approval_status

    _save_json(VERIFICATION_RUNS_PATH, current_state)
    return current_state


def load_verification_runs() -> dict:
    return sync_verification_runs()


def start_verification(note: str = "") -> dict:
    state = sync_verification_runs()
    proposal = state.get("proposal") or {}
    if not proposal or state.get("approval_status") != "approved":
        return state

    state["status"] = "pending"
    state["last_result"] = ""
    state["last_note"] = str(note or "").strip()
    state["last_checked_at"] = time.time()
    state["attempts"] = int(state.get("attempts", 0) or 0) + 1
    _save_json(VERIFICATION_RUNS_PATH, state)
    return state


def mark_verification_success(note: str = "") -> dict:
    state = sync_verification_runs()
    if state.get("approval_status") != "approved" or not state.get("proposal"):
        return state

    state["status"] = "success"
    state["last_result"] = "success"
    state["last_note"] = str(note or "").strip()
    state["last_checked_at"] = time.time()
    if int(state.get("attempts", 0) or 0) <= 0:
        state["attempts"] = 1
    _save_json(VERIFICATION_RUNS_PATH, state)
    return state


def mark_verification_failed(note: str = "") -> dict:
    state = sync_verification_runs()
    if state.get("approval_status") != "approved" or not state.get("proposal"):
        return state

    state["status"] = "failed"
    state["last_result"] = "failed"
    state["last_note"] = str(note or "").strip()
    state["last_checked_at"] = time.time()
    if int(state.get("attempts", 0) or 0) <= 0:
        state["attempts"] = 1
    _save_json(VERIFICATION_RUNS_PATH, state)
    return state


def retry_verification(note: str = "") -> dict:
    return start_verification(note=note or "nova tentativa solicitada")
