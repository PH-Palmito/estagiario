import json
import os
import time
from pathlib import Path

from memory.codex_inbox import latest_codex_inbox_item
from memory.execution_packages import load_execution_package


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
IMPLEMENTATION_HANDOFF_PATH = MEMORY_DIR / "implementation_handoff.json"
IMPLEMENTATION_HANDOFF_MD_PATH = MEMORY_DIR / "implementation_handoff.md"


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


def generate_implementation_handoff() -> dict:
    package = load_execution_package()
    decision = latest_codex_inbox_item("decision")
    next_step = latest_codex_inbox_item("next_step")

    if package.get("status") != "ready_for_codex":
        return {
            "generated_at": time.time(),
            "status": "blocked",
            "title": "",
            "reason": "Nenhum pacote de execucao aprovado esta pronto para implementacao.",
            "files": [],
            "instructions": [],
            "validation": [],
            "ready_definition": [],
        }

    title = str(package.get("title", "")).strip()
    files = [str(file) for file in package.get("files", []) if str(file).strip()]
    steps = [str(step) for step in package.get("steps", []) if str(step).strip()]
    validation = [str(command) for command in package.get("validation", []) if str(command).strip()]
    decision_text = str(decision.get("text", "")).strip()
    next_step_text = str(next_step.get("text", "")).strip()

    instructions = [
        "Leia os arquivos alvo antes de editar.",
        "Aplique a menor mudanca util possivel.",
        "Nao altere comportamento fora do escopo da acao candidata.",
        "Preserve mudancas existentes do usuario.",
    ]
    instructions.extend(steps[:5])

    ready_definition = [
        "Arquivos alvo foram alterados apenas quando necessario.",
        "Validacao sugerida foi executada ou a impossibilidade foi registrada.",
        "Resultado foi explicado de forma curta para o operador.",
        "Se falhar, registrar a falha para alimentar nova rodada do Axel.",
    ]

    payload = {
        "generated_at": time.time(),
        "status": "ready",
        "title": title,
        "files": files,
        "risk": str(package.get("risk", "")).strip(),
        "decision": decision_text,
        "next_step": next_step_text,
        "instructions": instructions,
        "validation": validation,
        "ready_definition": ready_definition,
    }
    return payload


def save_implementation_handoff() -> dict:
    payload = generate_implementation_handoff()
    _save_json(IMPLEMENTATION_HANDOFF_PATH, payload)

    markdown = [
        "# Handoff do Axel para o Codex",
        "",
        f"**Status:** {payload.get('status', '')}",
        f"**Titulo:** {payload.get('title', '')}",
        f"**Risco:** {payload.get('risk', '')}",
        "",
    ]
    decision = str(payload.get("decision", "")).strip()
    next_step = str(payload.get("next_step", "")).strip()
    if decision:
        markdown.extend(["## Decisao registrada", decision, ""])
    if next_step:
        markdown.extend(["## Proximo passo registrado", next_step, ""])

    markdown.append("## Arquivos alvo")
    for file in payload.get("files", []):
        markdown.append(f"- {file}")
    markdown.extend(["", "## Instrucoes"])
    for instruction in payload.get("instructions", []):
        markdown.append(f"- {instruction}")
    markdown.extend(["", "## Validacao"])
    for command in payload.get("validation", []):
        markdown.append(f"- `{command}`")
    markdown.extend(["", "## Definicao de pronto"])
    for item in payload.get("ready_definition", []):
        markdown.append(f"- {item}")
    if payload.get("status") == "blocked":
        markdown.extend(["", "## Bloqueio", payload.get("reason", "")])
    IMPLEMENTATION_HANDOFF_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")
    return payload


def load_implementation_handoff() -> dict:
    data = _load_json(IMPLEMENTATION_HANDOFF_PATH)
    if isinstance(data, dict) and data.get("status"):
        return data
    return save_implementation_handoff()
