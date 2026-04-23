import json
import os
import time
from pathlib import Path

from memory.handoff_applications import load_handoff_application
from memory.implementation_handoff import load_implementation_handoff


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
CODEX_IMPLEMENTATION_REQUEST_PATH = MEMORY_DIR / "codex_implementation_request.json"
CODEX_IMPLEMENTATION_REQUEST_MD_PATH = MEMORY_DIR / "codex_implementation_request.md"


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


def _bullet_lines(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items if str(item).strip()]


def generate_codex_implementation_request() -> dict:
    handoff = load_implementation_handoff()
    application = load_handoff_application()

    if handoff.get("status") != "ready":
        return {
            "generated_at": time.time(),
            "status": "blocked",
            "title": "",
            "message": "Ainda nao ha handoff pronto para transformar em pedido de implementacao.",
            "files": [],
            "validation": [],
            "prompt": "",
        }

    title = str(handoff.get("title", "")).strip()
    files = [str(file) for file in handoff.get("files", []) if str(file).strip()]
    instructions = [str(item) for item in handoff.get("instructions", []) if str(item).strip()]
    validation = [str(item) for item in handoff.get("validation", []) if str(item).strip()]
    ready_definition = [str(item) for item in handoff.get("ready_definition", []) if str(item).strip()]
    risk = str(handoff.get("risk", "")).strip()
    application_status = str(application.get("status", "ready")).strip()

    prompt_lines = [
        "Codex, aplique este handoff no projeto Axel.",
        "",
        f"Objetivo: {title}.",
        f"Status atual da aplicacao: {application_status}.",
    ]
    if risk:
        prompt_lines.append(f"Risco estimado: {risk}.")

    if files:
        prompt_lines.extend(["", "Arquivos alvo:"])
        prompt_lines.extend(_bullet_lines(files))

    if instructions:
        prompt_lines.extend(["", "Instrucoes de implementacao:"])
        prompt_lines.extend(_bullet_lines(instructions))

    if validation:
        prompt_lines.extend(["", "Validacao sugerida:"])
        prompt_lines.extend(_bullet_lines(validation))

    if ready_definition:
        prompt_lines.extend(["", "Definicao de pronto:"])
        prompt_lines.extend(_bullet_lines(ready_definition))

    prompt_lines.extend(
        [
            "",
            "Regras:",
            "- Leia os arquivos antes de editar.",
            "- Use a menor mudanca util possivel.",
            "- Preserve mudancas existentes do usuario.",
            "- Ao terminar, diga exatamente o que mudou, como validou e se existe risco restante.",
        ]
    )

    prompt = "\n".join(prompt_lines)
    return {
        "generated_at": time.time(),
        "status": "ready_for_codex",
        "title": title,
        "files": files,
        "risk": risk,
        "application_status": application_status,
        "validation": validation,
        "prompt": prompt,
        "message": "Pedido de implementacao pronto para enviar ao Codex.",
    }


def save_codex_implementation_request() -> dict:
    payload = generate_codex_implementation_request()
    _save_json(CODEX_IMPLEMENTATION_REQUEST_PATH, payload)

    markdown = [
        "# Pedido de implementacao para o Codex",
        "",
        f"**Status:** {payload.get('status', '')}",
        f"**Titulo:** {payload.get('title', '')}",
        "",
        "## Mensagem",
        payload.get("prompt", "") or payload.get("message", ""),
        "",
    ]
    CODEX_IMPLEMENTATION_REQUEST_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")
    return payload


def load_codex_implementation_request() -> dict:
    data = _load_json(CODEX_IMPLEMENTATION_REQUEST_PATH)
    if isinstance(data, dict) and data.get("status"):
        return data
    return save_codex_implementation_request()
