from __future__ import annotations

import re
import time
from pathlib import Path

from memory.json_store import read_json_file, write_json_atomic

TASK_EVALUATIONS_PATH = Path("memory/task_evaluations.json")
MAX_EVALUATIONS = 240
VALID_STATUSES = {"success", "failure", "needs_adjustment"}


def _compact(text: str, limit: int = 220) -> str:
    clean = re.sub(r"\s+", " ", str(text or "")).strip(" .")
    if len(clean) > limit:
        return clean[: max(0, limit - 3)].rstrip() + "..."
    return clean


def _normalize_status(status: str, *, success: bool | None = None) -> str:
    normalized = str(status or "").strip().lower()
    normalized_key = re.sub(r"\s+", "_", normalized)
    aliases = {
        "ok": "success",
        "funcionou": "success",
        "sucesso": "success",
        "success": "success",
        "falhou": "failure",
        "erro": "failure",
        "failure": "failure",
        "failed": "failure",
        "nao_funcionou": "failure",
        "nao funcionou": "failure",
        "não_funcionou": "failure",
        "não funcionou": "failure",
        "não_funcionou": "failure",
        "ajuste": "needs_adjustment",
        "needs_adjustment": "needs_adjustment",
        "precisa_ajuste": "needs_adjustment",
        "precisa_de_ajuste": "needs_adjustment",
        "precisa ajuste": "needs_adjustment",
        "precisa de ajuste": "needs_adjustment",
    }
    if normalized in aliases:
        return aliases[normalized]
    if normalized_key in aliases:
        return aliases[normalized_key]
    if success is not None:
        return "success" if success else "failure"
    return "needs_adjustment"


def load_task_evaluations(path: Path | None = None) -> dict:
    data = read_json_file(path or TASK_EVALUATIONS_PATH, {"items": []}, validator=lambda value: isinstance(value, dict))
    items = data.get("items") if isinstance(data.get("items"), list) else []
    return {"updated_at": data.get("updated_at", 0.0), "items": [item for item in items if isinstance(item, dict)]}


def _save_items(items: list[dict], path: Path | None = None) -> dict:
    payload = {
        "updated_at": time.time(),
        "items": list(items or [])[:MAX_EVALUATIONS],
    }
    write_json_atomic(path or TASK_EVALUATIONS_PATH, payload, indent=2, trailing_newline=True)
    return payload


def record_task_evaluation(
    *,
    action: str,
    status: str = "",
    success: bool | None = None,
    source: str = "auto",
    note: str = "",
    result: str = "",
    error: str = "",
    metadata: dict | None = None,
    path: Path | None = None,
) -> dict:
    now = time.time()
    action_name = str(action or "unknown").strip() or "unknown"
    item = {
        "id": f"eval-{time.time_ns()}",
        "action": action_name,
        "status": _normalize_status(status, success=success),
        "source": str(source or "auto").strip() or "auto",
        "note": _compact(note),
        "result": _compact(result),
        "error": _compact(error),
        "metadata": dict(metadata or {}),
        "created_at": now,
        "updated_at": now,
    }
    data = load_task_evaluations(path)
    items = [item] + list(data.get("items") or [])
    _save_items(items, path)
    return item


def update_latest_task_evaluation(status: str, *, note: str = "", source: str = "user", path: Path | None = None) -> dict:
    data = load_task_evaluations(path)
    items = list(data.get("items") or [])
    if not items:
        return {}
    current = dict(items[0])
    current["status"] = _normalize_status(status)
    current["source"] = str(source or "user").strip() or "user"
    if note:
        current["note"] = _compact(note)
    current["updated_at"] = time.time()
    items[0] = current
    _save_items(items, path)
    return current


def latest_task_evaluation(path: Path | None = None) -> dict:
    items = load_task_evaluations(path).get("items") or []
    return dict(items[0]) if items else {}


def task_evaluation_summary(limit: int = 80, *, path: Path | None = None) -> dict:
    items = list(load_task_evaluations(path).get("items") or [])[: max(1, int(limit))]
    counts = {"success": 0, "failure": 0, "needs_adjustment": 0}
    by_action: dict[str, dict] = {}
    for item in items:
        status = _normalize_status(str(item.get("status") or ""))
        counts[status] = counts.get(status, 0) + 1
        action = str(item.get("action") or "unknown").strip() or "unknown"
        action_stats = by_action.setdefault(action, {"action": action, "total": 0, "success": 0, "failure": 0, "needs_adjustment": 0})
        action_stats["total"] += 1
        action_stats[status] = int(action_stats.get(status) or 0) + 1
    ranked_actions = sorted(by_action.values(), key=lambda value: (int(value.get("failure") or 0), int(value.get("needs_adjustment") or 0), int(value.get("total") or 0)), reverse=True)
    total = len(items)
    return {
        "total": total,
        "counts": counts,
        "success_rate": round(counts.get("success", 0) / total, 3) if total else 0.0,
        "recent": items[:8],
        "by_action": ranked_actions[:8],
    }


def format_task_evaluation_summary(limit: int = 80) -> str:
    summary = task_evaluation_summary(limit=limit)
    total = int(summary.get("total") or 0)
    if not total:
        return "Ainda nao ha autoavaliacoes de tarefas salvas."
    counts = summary.get("counts") or {}
    parts = [
        "Autoavaliacao de tarefas: "
        f"{total} registro(s), {counts.get('success', 0)} sucesso(s), "
        f"{counts.get('failure', 0)} falha(s), {counts.get('needs_adjustment', 0)} ajuste(s)."
    ]
    recent = summary.get("recent") or []
    if recent:
        item = recent[0]
        parts.append(f"Ultima: {item.get('action', 'unknown')} -> {item.get('status', '')}.")
    by_action = summary.get("by_action") or []
    if by_action:
        parts.append("Mais sensiveis: " + "; ".join(f"{item['action']} ({item['failure']} falha, {item['needs_adjustment']} ajuste)" for item in by_action[:3]) + ".")
    return " ".join(parts)


def format_latest_task_evaluation() -> str:
    item = latest_task_evaluation()
    if not item:
        return "Ainda nao ha autoavaliacao recente."
    note = str(item.get("note") or item.get("error") or item.get("result") or "").strip()
    detail = f" Detalhe: {note}." if note else ""
    return f"Ultima autoavaliacao: {item.get('action', 'unknown')} -> {item.get('status', '')}.{detail}"
