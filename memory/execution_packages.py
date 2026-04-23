import json
import os
import time
from pathlib import Path

from memory.action_candidates import load_action_candidates


ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
EXECUTION_PACKAGES_PATH = MEMORY_DIR / "execution_packages.json"
EXECUTION_PACKAGE_MD_PATH = MEMORY_DIR / "execution_package.md"


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


def _validation_commands(files: list[str]) -> list[str]:
    py_files = [file for file in files if str(file).endswith(".py")]
    commands = []
    if py_files:
        joined = " ".join(f".\\{file}" for file in py_files)
        commands.append(f".\\venv\\Scripts\\python.exe -m py_compile {joined}")
    commands.append(".\\venv\\Scripts\\python.exe .\\main.py --voice --hotword")
    return commands


def _approved_action() -> dict:
    candidates = load_action_candidates()
    for candidate in candidates:
        if isinstance(candidate, dict) and str(candidate.get("status", "")).strip() == "approved":
            return candidate
    return {}


def generate_execution_package() -> dict:
    action = _approved_action()
    if not action:
        return {
            "generated_at": time.time(),
            "status": "waiting_for_approval",
            "title": "",
            "message": "Nenhuma acao candidata aprovada para empacotar.",
            "files": [],
            "steps": [],
            "validation": [],
        }

    files = [str(file) for file in action.get("files", []) if str(file).strip()]
    steps = [str(step) for step in action.get("steps", []) if str(step).strip()]
    title = str(action.get("title", "")).strip()
    risk = str(action.get("risk", "Medio.")).strip()

    package = {
        "generated_at": time.time(),
        "status": "ready_for_codex",
        "title": title,
        "source": str(action.get("source", "")).strip(),
        "risk": risk,
        "files": files,
        "steps": steps,
        "validation": _validation_commands(files),
        "message": (
            "Pacote de execucao pronto para aplicacao supervisionada. "
            "O Axel ainda nao deve aplicar sozinho; o Codex deve revisar, editar e validar."
        ),
    }
    return package


def save_execution_package() -> dict:
    payload = generate_execution_package()
    _save_json(EXECUTION_PACKAGES_PATH, payload)

    markdown = [
        "# Pacote de execucao do Axel",
        "",
        f"**Status:** {payload.get('status', '')}",
        f"**Titulo:** {payload.get('title', '')}",
        f"**Risco:** {payload.get('risk', '')}",
        "",
        "## Arquivos alvo",
    ]
    for file in payload.get("files", []):
        markdown.append(f"- {file}")
    markdown.extend(["", "## Passos sugeridos"])
    for step in payload.get("steps", []):
        markdown.append(f"- {step}")
    markdown.extend(["", "## Validacao sugerida"])
    for command in payload.get("validation", []):
        markdown.append(f"- `{command}`")
    markdown.extend(["", "## Observacao", payload.get("message", "")])
    EXECUTION_PACKAGE_MD_PATH.write_text("\n".join(markdown), encoding="utf-8")
    return payload


def load_execution_package() -> dict:
    data = _load_json(EXECUTION_PACKAGES_PATH)
    if isinstance(data, dict) and data.get("status"):
        return data
    return save_execution_package()
