import json
import os
import time
from pathlib import Path

from memory.patch_proposals import load_patch_proposals

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
APPROVAL_GATE_PATH = MEMORY_DIR / "approval_gate.json"


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


def _default_state() -> dict:
    proposals = load_patch_proposals()
    current = proposals[0] if proposals else {}
    return {
        "generated_at": time.time(),
        "status": "pending" if current else "none",
        "proposal_key": _proposal_key(current) if current else "",
        "proposal": current,
        "decision_note": "",
        "decided_at": 0.0,
    }


def sync_approval_gate() -> dict:
    current_state = _load_json(APPROVAL_GATE_PATH)
    if not isinstance(current_state, dict) or "status" not in current_state:
        current_state = _default_state()

    proposals = load_patch_proposals()
    current = proposals[0] if proposals else {}
    current_key = _proposal_key(current) if current else ""
    old_key = str(current_state.get("proposal_key", "")).strip()

    if current_key != old_key:
        current_state = {
            "generated_at": time.time(),
            "status": "pending" if current else "none",
            "proposal_key": current_key,
            "proposal": current,
            "decision_note": "",
            "decided_at": 0.0,
        }

    _save_json(APPROVAL_GATE_PATH, current_state)
    return current_state


def load_approval_gate() -> dict:
    return sync_approval_gate()


def approve_current_proposal(note: str = "") -> dict:
    state = sync_approval_gate()
    state["status"] = "approved"
    state["decision_note"] = str(note or "").strip()
    state["decided_at"] = time.time()
    _save_json(APPROVAL_GATE_PATH, state)
    return state


def reject_current_proposal(note: str = "") -> dict:
    state = sync_approval_gate()
    state["status"] = "rejected"
    state["decision_note"] = str(note or "").strip()
    state["decided_at"] = time.time()
    _save_json(APPROVAL_GATE_PATH, state)
    return state


def reset_current_proposal(note: str = "") -> dict:
    state = sync_approval_gate()
    if state.get("proposal"):
        state["status"] = "pending"
    else:
        state["status"] = "none"
    state["decision_note"] = str(note or "").strip()
    state["decided_at"] = 0.0
    _save_json(APPROVAL_GATE_PATH, state)
    return state
