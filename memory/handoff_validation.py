import json
import os
import time
from pathlib import Path

from memory.codex_inbox import latest_codex_inbox_item
from memory.handoff_applications import load_handoff_application


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
HANDOFF_VALIDATION_PATH = MEMORY_DIR / "handoff_validation.json"
HANDOFF_VALIDATION_MD_PATH = MEMORY_DIR / "handoff_validation.md"


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


def _handoff_key(handoff: dict) -> str:
    title = str(handoff.get("title", "")).strip().lower()
    files = ",".join(str(item) for item in handoff.get("files", []))
    return f"{title}|{files}"


def _clean_items(items: list, limit: int = 8) -> list[str]:
    cleaned = []
    for item in items:
        text = str(item or "").strip()
        if text and text not in cleaned:
            cleaned.append(text)
        if len(cleaned) >= limit:
            break
    return cleaned


def generate_handoff_validation() -> dict:
    application = load_handoff_application()
    handoff = application.get("handoff") or {}
    status = str(application.get("status", "blocked")).strip()
    title = str(handoff.get("title", "")).strip()

    if not title or status in {"blocked", "ready"}:
        return {
            "generated_at": time.time(),
            "status": "blocked",
            "handoff_key": _handoff_key(handoff) if title else "",
            "title": title,
            "message": "Ainda nao ha handoff aplicado para validar.",
            "checklist": [],
            "evidence": [],
        }

    validation = _clean_items(handoff.get("validation") or [], limit=4)
    ready_definition = _clean_items(handoff.get("ready_definition") or [], limit=4)
    applied = latest_codex_inbox_item("implementation_applied")
    failed = latest_codex_inbox_item("implementation_failed")

    checklist = []
    checklist.extend(validation)
    checklist.extend(ready_definition)
    checklist.extend(
        [
            "Abrir o fluxo afetado e repetir o comando que motivou a melhoria.",
            "Confirmar que o Axel respondeu corretamente sem executar acao inesperada.",
            "Se falhar, dizer 'handoff falhou' ou 'codex falhou' com uma frase curta sobre o erro.",
            "Se funcionar, dizer 'handoff validado' para fechar o ciclo.",
        ]
    )
    checklist = _clean_items(checklist, limit=8)

    evidence = []
    applied_text = str(applied.get("text", "")).strip()
    failed_text = str(failed.get("text", "")).strip()
    if applied_text:
        evidence.append(f"Codex aplicou: {applied_text}")
    if failed_text and status == "failed":
        evidence.append(f"Falha registrada: {failed_text}")
    note = str(application.get("last_note", "")).strip()
    if note:
        evidence.append(f"Nota atual: {note}")

    return {
        "generated_at": time.time(),
        "status": "ready" if status in {"applied", "in_progress", "failed"} else status,
        "handoff_status": status,
        "handoff_key": _handoff_key(handoff),
        "title": title,
        "checklist": checklist,
        "evidence": evidence,
        "message": "Checklist de validacao pronto.",
    }


def save_handoff_validation() -> dict:
    payload = generate_handoff_validation()
    _save_json(HANDOFF_VALIDATION_PATH, payload)

    markdown = [
        "# Checklist de validacao do handoff",
        "",
        f"**Status:** {payload.get('status', '')}",
        f"**Handoff:** {payload.get('title', '')}",
        "",
        "## Checklist",
    ]
    for item in payload.get("checklist", []):
        markdown.append(f"- [ ] {item}")
    evidence = payload.get("evidence") or []
    if evidence:
        markdown.extend(["", "## Evidencias"])
        for item in evidence:
            markdown.append(f"- {item}")
    if payload.get("status") == "blocked":
        markdown.extend(["", "## Bloqueio", payload.get("message", "")])
    HANDOFF_VALIDATION_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")
    return payload


def load_handoff_validation() -> dict:
    data = _load_json(HANDOFF_VALIDATION_PATH)
    if isinstance(data, dict) and data.get("status"):
        return data
    return save_handoff_validation()
