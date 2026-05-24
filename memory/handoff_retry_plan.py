import json
import os
import time
from pathlib import Path

from memory.codex_inbox import latest_codex_inbox_item
from memory.handoff_applications import load_handoff_application
from memory.handoff_validation import load_handoff_validation

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
HANDOFF_RETRY_PLAN_PATH = MEMORY_DIR / "handoff_retry_plan.json"
HANDOFF_RETRY_PLAN_MD_PATH = MEMORY_DIR / "handoff_retry_plan.md"


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


def generate_handoff_retry_plan() -> dict:
    application = load_handoff_application()
    validation = load_handoff_validation()
    handoff = application.get("handoff") or {}
    title = str(handoff.get("title", "")).strip()
    application_status = str(application.get("status", "blocked")).strip()
    validation_status = str(validation.get("status", "blocked")).strip()
    failed_reply = latest_codex_inbox_item("implementation_failed")

    has_failure = application_status == "failed" or bool(str(failed_reply.get("text", "")).strip())
    if not title or not has_failure:
        return {
            "generated_at": time.time(),
            "status": "blocked",
            "title": title,
            "handoff_key": _handoff_key(handoff) if title else "",
            "reason": "Ainda nao ha falha de handoff suficiente para replanejar.",
            "files": [],
            "evidence": [],
            "steps": [],
            "validation": [],
        }

    files = [str(file) for file in handoff.get("files", []) if str(file).strip()]
    evidence = []
    failure_text = str(failed_reply.get("text", "")).strip()
    note = str(application.get("last_note", "")).strip()
    if failure_text:
        evidence.append(f"Resposta de falha do Codex: {failure_text}")
    if note:
        evidence.append(f"Nota da aplicacao: {note}")
    for item in validation.get("evidence") or []:
        text = str(item).strip()
        if text and text not in evidence:
            evidence.append(text)

    steps = [
        "Reproduzir a falha com o mesmo comando ou fluxo usado na validacao.",
        "Ler novamente os arquivos alvo antes de editar.",
        "Comparar o comportamento esperado com o comportamento observado.",
        "Aplicar um patch menor e mais especifico que a tentativa anterior.",
        "Executar a validacao sugerida antes de marcar como aplicado.",
    ]
    validation_commands = [str(item) for item in handoff.get("validation", []) if str(item).strip()]
    if not validation_commands:
        validation_commands = [".\\venv\\Scripts\\python.exe -m py_compile .\\main.py"]

    return {
        "generated_at": time.time(),
        "status": "ready_for_codex",
        "title": f"Nova tentativa para: {title}",
        "handoff_key": _handoff_key(handoff),
        "application_status": application_status,
        "validation_status": validation_status,
        "files": files,
        "evidence": evidence[:8],
        "steps": steps,
        "validation": validation_commands[:4],
        "message": "Plano de nova tentativa pronto para o Codex.",
    }


def save_handoff_retry_plan() -> dict:
    payload = generate_handoff_retry_plan()
    _save_json(HANDOFF_RETRY_PLAN_PATH, payload)

    markdown = [
        "# Plano de nova tentativa do handoff",
        "",
        f"**Status:** {payload.get('status', '')}",
        f"**Titulo:** {payload.get('title', '')}",
        "",
        "## Evidencias",
    ]
    for item in payload.get("evidence", []):
        markdown.append(f"- {item}")
    markdown.extend(["", "## Arquivos alvo"])
    for file in payload.get("files", []):
        markdown.append(f"- {file}")
    markdown.extend(["", "## Passos"])
    for item in payload.get("steps", []):
        markdown.append(f"- {item}")
    markdown.extend(["", "## Validacao"])
    for item in payload.get("validation", []):
        markdown.append(f"- `{item}`")
    if payload.get("status") == "blocked":
        markdown.extend(["", "## Bloqueio", payload.get("reason", "")])
    HANDOFF_RETRY_PLAN_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")
    return payload


def load_handoff_retry_plan() -> dict:
    data = _load_json(HANDOFF_RETRY_PLAN_PATH)
    if isinstance(data, dict) and data.get("status"):
        return data
    return save_handoff_retry_plan()
