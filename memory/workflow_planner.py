from __future__ import annotations

import re
import time
from pathlib import Path

from memory.json_store import read_json_file, write_json_atomic

ROOT = Path(__file__).resolve().parents[1]
MEMORY_DIR = ROOT / "memory"
WORKFLOW_DIR = MEMORY_DIR / "workflows"
WORKFLOW_INDEX_PATH = WORKFLOW_DIR / "index.json"

DEFAULT_TASKS = [
    "Definir objetivo, restricoes e criterio de pronto.",
    "Levantar contexto, arquivos, fontes ou dados necessarios.",
    "Separar riscos, dependencias e pontos que exigem confirmacao.",
    "Executar a solucao em etapas pequenas e verificaveis.",
    "Testar, registrar resultado e fechar com resumo.",
]


def _now() -> float:
    return time.time()


def _slugify(text: str, limit: int = 48) -> str:
    clean = str(text or "").strip().lower()
    clean = re.sub(r"[^\w\s-]", " ", clean, flags=re.UNICODE)
    clean = re.sub(r"[\s_-]+", "-", clean).strip("-")
    return (clean[:limit].strip("-") or "workflow")


def _format_ts(value: float | int | str | None) -> str:
    try:
        return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(float(value or 0)))
    except Exception:
        return ""


def _load_index(path: Path | None = None) -> dict:
    index_path = path or WORKFLOW_INDEX_PATH
    data = read_json_file(index_path, {"plans": []}, validator=lambda value: isinstance(value, dict))
    plans = data.get("plans") if isinstance(data, dict) else []
    data["plans"] = [item for item in plans if isinstance(item, dict)] if isinstance(plans, list) else []
    return data


def _save_index(data: dict, path: Path | None = None) -> dict:
    index_path = path or WORKFLOW_INDEX_PATH
    payload = dict(data or {})
    payload["plans"] = [item for item in payload.get("plans", []) if isinstance(item, dict)]
    payload["updated_at"] = _now()
    write_json_atomic(index_path, payload, indent=2, trailing_newline=True)
    return payload


def _workflow_path(plan_id: str, title: str, workflow_dir: Path | None = None) -> Path:
    directory = workflow_dir or WORKFLOW_DIR
    return directory / f"{plan_id}-{_slugify(title)}.md"


def _normalize_tasks(tasks: list[str] | None = None) -> list[dict]:
    raw_tasks = tasks or DEFAULT_TASKS
    normalized = []
    for index, task in enumerate(raw_tasks, start=1):
        text = re.sub(r"\s+", " ", str(task or "")).strip(" .")
        if text:
            normalized.append({"index": index, "text": text + ".", "status": "pending"})
    return normalized or _normalize_tasks(DEFAULT_TASKS)


def _render_plan(plan: dict) -> str:
    tasks = plan.get("tasks") or []
    lines = [
        f"# {plan.get('title', 'Workflow')}",
        "",
        f"- ID: {plan.get('id', '')}",
        f"- Status: {plan.get('status', 'active')}",
        f"- Criado: {_format_ts(plan.get('created_at'))}",
        f"- Atualizado: {_format_ts(plan.get('updated_at'))}",
        "",
        "## Ideia",
        str(plan.get("idea") or "Pendente.").strip(),
        "",
        "## Pesquisa",
        str(plan.get("research") or "- Pendente.").strip(),
        "",
        "## Gate",
        f"- Status: {plan.get('gate_status', 'pending')}",
        f"- Criterio: {plan.get('gate_criteria', 'confirmar escopo, risco e proxima acao antes de executar')}",
        "",
        "## Design",
        str(plan.get("design") or "- Pendente.").strip(),
        "",
        "## Plano",
    ]
    for task in tasks:
        marker = "x" if task.get("status") == "done" else " "
        status_note = "" if task.get("status") in {"pending", "done"} else f" ({task.get('status')})"
        lines.append(f"- [{marker}] {task.get('index')}. {task.get('text', '').strip()}{status_note}")
    lines.extend(
        [
            "",
            "## Handoff",
            str(plan.get("handoff") or "- Sem handoff registrado.").strip(),
            "",
            "## Fechamento",
            str(plan.get("closure") or "- Aberto.").strip(),
            "",
        ]
    )
    return "\n".join(lines)


def _write_plan(plan: dict) -> dict:
    path = Path(str(plan.get("path") or ""))
    path.parent.mkdir(parents=True, exist_ok=True)
    plan["updated_at"] = _now()
    path.write_text(_render_plan(plan), encoding="utf-8")
    return plan


def _index_entry(plan: dict) -> dict:
    tasks = plan.get("tasks") or []
    completed = [task for task in tasks if task.get("status") == "done"]
    current = next((task for task in tasks if task.get("status") != "done"), {})
    return {
        "id": plan.get("id", ""),
        "title": plan.get("title", ""),
        "status": plan.get("status", "active"),
        "path": plan.get("path", ""),
        "created_at": plan.get("created_at"),
        "updated_at": plan.get("updated_at"),
        "current_step": current.get("text", ""),
        "completed_steps": len(completed),
        "total_steps": len(tasks),
    }


def _upsert_index(plan: dict) -> None:
    index = _load_index()
    entry = _index_entry(plan)
    plans = [item for item in index.get("plans", []) if item.get("id") != plan.get("id")]
    plans.insert(0, entry)
    index["plans"] = plans[:40]
    _save_index(index)


def create_workflow_plan(title: str, *, idea: str | None = None, tasks: list[str] | None = None) -> dict:
    clean_title = re.sub(r"\s+", " ", str(title or "")).strip(" .")
    if not clean_title:
        clean_title = "Tarefa grande"
    created_at = _now()
    plan_id = time.strftime("wf-%Y%m%d-%H%M%S", time.localtime(created_at))
    path = _workflow_path(plan_id, clean_title)
    plan = {
        "id": plan_id,
        "title": clean_title,
        "status": "active",
        "created_at": created_at,
        "updated_at": created_at,
        "path": str(path),
        "idea": idea or clean_title,
        "research": "- Pendente.",
        "gate_status": "pending",
        "gate_criteria": "confirmar escopo, risco e proxima acao antes de executar",
        "design": "- Pendente.",
        "tasks": _normalize_tasks(tasks),
        "handoff": "- Sem handoff registrado.",
        "closure": "- Aberto.",
    }
    _write_plan(plan)
    _upsert_index(plan)
    return plan


def list_workflow_plans(limit: int = 5) -> list[dict]:
    index = _load_index()
    return list(index.get("plans", []))[: max(1, limit)]


def latest_workflow_plan(include_done: bool = False) -> dict:
    for item in list_workflow_plans(limit=20):
        if include_done or item.get("status") != "done":
            return load_workflow_plan(str(item.get("id", "")))
    return {}


def load_workflow_plan(plan_id: str = "") -> dict:
    target_id = str(plan_id or "").strip()
    index = _load_index()
    candidates = index.get("plans", [])
    if not target_id and candidates:
        target_id = str(candidates[0].get("id", ""))
    entry = next((item for item in candidates if item.get("id") == target_id), {})
    path = Path(str(entry.get("path") or ""))
    if not path.exists():
        return dict(entry) if entry else {}

    return {
        **entry,
        "content": path.read_text(encoding="utf-8", errors="replace"),
    }


def update_workflow_step(step_index: int, status: str = "done", plan_id: str = "") -> dict:
    index = _load_index()
    target_entry = {}
    if plan_id:
        target_entry = next((item for item in index.get("plans", []) if item.get("id") == plan_id), {})
    else:
        target_entry = next((item for item in index.get("plans", []) if item.get("status") != "done"), {})
    if not target_entry:
        return {}

    path = Path(str(target_entry.get("path") or ""))
    plan = _plan_from_index_entry(target_entry)
    tasks = plan.get("tasks") or []
    if step_index < 1 or step_index > len(tasks):
        return {}
    tasks[step_index - 1]["status"] = status
    if tasks and all(task.get("status") == "done" for task in tasks):
        plan["status"] = "done"
        plan["closure"] = "- Todas as etapas foram marcadas como concluidas."
    plan["path"] = str(path)
    _write_plan(plan)
    _upsert_index(plan)
    return _index_entry(plan)


def close_workflow_plan(summary: str = "", plan_id: str = "") -> dict:
    plan = _plan_from_index_entry(latest_workflow_plan(include_done=True) if not plan_id else _find_index_entry(plan_id))
    if not plan:
        return {}
    plan["status"] = "done"
    plan["closure"] = "- " + (re.sub(r"\s+", " ", str(summary or "")).strip(" .") or "Plano fechado.")
    _write_plan(plan)
    _upsert_index(plan)
    return _index_entry(plan)


def _find_index_entry(plan_id: str) -> dict:
    index = _load_index()
    return next((item for item in index.get("plans", []) if item.get("id") == plan_id), {})


def _plan_from_index_entry(entry: dict) -> dict:
    if not entry:
        return {}
    path = Path(str(entry.get("path") or ""))
    title = str(entry.get("title") or "Workflow")
    tasks = _parse_tasks_from_markdown(path.read_text(encoding="utf-8", errors="replace") if path.exists() else "")
    return {
        "id": entry.get("id", ""),
        "title": title,
        "status": entry.get("status", "active"),
        "created_at": entry.get("created_at") or _now(),
        "updated_at": entry.get("updated_at") or _now(),
        "path": str(path),
        "idea": _extract_section(path, "Ideia") or title,
        "research": _extract_section(path, "Pesquisa") or "- Pendente.",
        "gate_status": "pending",
        "gate_criteria": "confirmar escopo, risco e proxima acao antes de executar",
        "design": _extract_section(path, "Design") or "- Pendente.",
        "tasks": tasks or _normalize_tasks(),
        "handoff": _extract_section(path, "Handoff") or "- Sem handoff registrado.",
        "closure": _extract_section(path, "Fechamento") or "- Aberto.",
    }


def _extract_section(path: Path, section: str) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"^## {re.escape(section)}\s*\n(.+?)(?=^## |\Z)", text, flags=re.S | re.M)
    return match.group(1).strip() if match else ""


def _parse_tasks_from_markdown(text: str) -> list[dict]:
    tasks = []
    for line in str(text or "").splitlines():
        match = re.match(r"^-\s+\[([ xX])\]\s+(\d+)\.\s+(.+)$", line.strip())
        if not match:
            continue
        status = "done" if match.group(1).lower() == "x" else "pending"
        task_text = re.sub(r"\s+\((blocked|skipped|failed)\)$", "", match.group(3).strip())
        status_match = re.search(r"\((blocked|skipped|failed)\)$", match.group(3).strip())
        if status_match:
            status = status_match.group(1)
        tasks.append({"index": int(match.group(2)), "text": task_text, "status": status})
    return tasks


def format_workflow_plan(plan: dict | None = None) -> str:
    data = plan or latest_workflow_plan()
    if not data:
        return "Ainda nao ha workflow duravel criado."
    title = str(data.get("title") or "Workflow").strip()
    status = str(data.get("status") or "active").strip()
    current = str(data.get("current_step") or "").strip()
    completed = int(data.get("completed_steps") or 0)
    total = int(data.get("total_steps") or 0)
    path = str(data.get("path") or "").strip()
    parts = [f"Workflow atual: {title} ({status})."]
    if total:
        parts.append(f"Progresso: {completed}/{total}.")
    if current:
        parts.append(f"Proxima etapa: {current}")
    if path:
        parts.append(f"Arquivo: {path}.")
    return " ".join(parts)


def format_workflow_list(limit: int = 5) -> str:
    plans = list_workflow_plans(limit=limit)
    if not plans:
        return "Ainda nao ha workflows duraveis salvos."
    lines = ["Workflows duraveis:"]
    for index, plan in enumerate(plans, start=1):
        lines.append(
            f"{index}. {plan.get('title', 'Workflow')} ({plan.get('status', 'active')}) "
            f"{plan.get('completed_steps', 0)}/{plan.get('total_steps', 0)}"
        )
    return " ".join(lines)
