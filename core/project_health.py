from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from time import time

PROJECT_JSON_FILES = [
    "memory/routines.json",
    "memory/ui_state.json",
    "memory/operational_context.json",
    "memory/operational_memory.json",
    "memory/auto_advances.json",
    "memory/bottlenecks.json",
    "memory/self_evolution.json",
]

KEY_MODULES = [
    "main.py",
    "core/router.py",
    "core/normalizer.py",
    "core/validator.py",
    "memory/operational_context.py",
    "memory/auto_advances.py",
    "tools/briefing_tools.py",
    "ui/qt_axel_hud.py",
]


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def validate_project_jsons(root: Path | None = None) -> tuple[list[str], list[str]]:
    project_dir = root or project_root()
    ok = []
    errors = []
    for relative in PROJECT_JSON_FILES:
        path = project_dir / relative
        if not path.exists():
            continue
        try:
            json.loads(path.read_text(encoding="utf-8"))
            ok.append(relative)
        except Exception as exc:
            errors.append(f"{relative}: {exc}")
    return ok, errors


def compile_project_modules(root: Path | None = None) -> tuple[list[str], str]:
    project_dir = root or project_root()
    existing = [item for item in KEY_MODULES if (project_dir / item).exists()]
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", *existing],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=45,
        )
    except Exception as exc:
        return [], str(exc)
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        return [], detail[:500] or f"py_compile retornou codigo {result.returncode}"
    return existing, ""


def project_change_summary(root: Path | None = None, limit: int = 4) -> str:
    project_dir = root or project_root()
    if not (project_dir / ".git").exists():
        return "sem repositorio git local detectado"
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={project_dir.as_posix()}", "status", "--short"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
            timeout=8,
        )
    except Exception:
        return "status git indisponivel"
    if result.returncode != 0:
        return "status git indisponivel"
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        return "sem arquivos alterados no git"
    shown = "; ".join(lines[:limit])
    if len(lines) > limit:
        shown += f"; +{len(lines) - limit} outros"
    return shown


def run_estagiario_preflight(root: Path | None = None) -> dict:
    compiled, compile_error = compile_project_modules(root)
    json_ok, json_errors = validate_project_jsons(root)
    return {
        "compiled_modules": compiled,
        "compile_error": compile_error,
        "json_ok_count": len(json_ok),
        "json_errors": json_errors,
        "change_summary": project_change_summary(root),
    }


def _read_recent_jsonl(path: Path, limit: int = 30) -> list[dict]:
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()[-max(1, limit):]
    except Exception:
        return []
    events = []
    for line in lines:
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def recent_execution_summary(root: Path | None = None, limit: int = 30) -> dict:
    project_dir = root or project_root()
    events = _read_recent_jsonl(project_dir / "memory" / "execution_log.jsonl", limit=limit)
    commands = []
    errors = []
    for event in events:
        event_type = str(event.get("event") or "").strip()
        data = event.get("data") if isinstance(event.get("data"), dict) else {}
        message = str(data.get("message") or data.get("text") or data.get("command") or "").strip()
        if event_type in {"user_input", "ui_command"} and message:
            commands.append(message)
        if "error" in event_type.lower() or message.lower().startswith(("erro", "falha")):
            errors.append(message or event_type)
    return {
        "events_count": len(events),
        "recent_commands": commands[-5:],
        "recent_errors": errors[-5:],
    }


def memory_artifact_summary(root: Path | None = None) -> dict:
    project_dir = root or project_root()
    memory_dir = project_dir / "memory"
    patterns = {
        "json": "*.json",
        "jsonl": "*.jsonl",
        "tmp": "*.tmp",
        "html": "*.html",
        "txt": "*.txt",
    }
    counts = {}
    for name, pattern in patterns.items():
        try:
            counts[name] = len(list(memory_dir.glob(pattern)))
        except Exception:
            counts[name] = 0
    return counts


def action_catalog_summary() -> dict:
    try:
        from actions import ensure_default_actions, list_actions

        ensure_default_actions()
        actions = list_actions()
    except Exception as exc:
        return {"count": 0, "categories": {}, "error": str(exc)}

    categories: dict[str, int] = {}
    for action in actions:
        category = str(getattr(action, "category", "") or "general")
        categories[category] = categories.get(category, 0) + 1
    return {"count": len(actions), "categories": categories, "error": ""}


def build_project_health_snapshot(root: Path | None = None) -> dict:
    preflight = run_estagiario_preflight(root)
    execution = recent_execution_summary(root)
    artifacts = memory_artifact_summary(root)
    actions = action_catalog_summary()
    healthy = not preflight.get("compile_error") and not preflight.get("json_errors") and not actions.get("error")
    return {
        "generated_at": time(),
        "status": "saudavel" if healthy else "precisa de atencao",
        "preflight": preflight,
        "execution": execution,
        "artifacts": artifacts,
        "actions": actions,
    }


def format_project_health_panel(snapshot: dict | None = None) -> str:
    data = snapshot or build_project_health_snapshot()
    preflight = data.get("preflight") or {}
    execution = data.get("execution") or {}
    actions = data.get("actions") or {}
    artifacts = data.get("artifacts") or {}

    parts = [f"Saude do Axel: projeto {data.get('status', 'indefinido')}."]
    if preflight.get("compile_error"):
        parts.append(f"Compilacao com falha: {preflight.get('compile_error')}.")
    else:
        parts.append(f"Compilacao ok em {len(preflight.get('compiled_modules') or [])} modulos-chave.")

    json_errors = preflight.get("json_errors") or []
    if json_errors:
        parts.append(f"Memorias JSON com erro: {json_errors[0]}.")
    else:
        parts.append(f"Memorias JSON ok: {preflight.get('json_ok_count', 0)} arquivos.")

    action_error = actions.get("error")
    if action_error:
        parts.append(f"Catalogo de actions com alerta: {action_error}.")
    else:
        parts.append(f"Actions registradas: {actions.get('count', 0)}.")

    errors = execution.get("recent_errors") or []
    if errors:
        parts.append(f"Erros recentes: {errors[-1]}.")
    else:
        parts.append("Sem erro recente no log operacional.")

    parts.append(
        "Artefatos locais em memory: "
        f"{artifacts.get('json', 0)} json, {artifacts.get('tmp', 0)} tmp, "
        f"{artifacts.get('html', 0) + artifacts.get('txt', 0)} html/txt."
    )
    parts.append(f"Git: {preflight.get('change_summary')}.")
    return " ".join(parts)
