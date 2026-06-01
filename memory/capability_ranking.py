from __future__ import annotations

from math import log1p
from pathlib import Path

from memory.task_evaluation import load_task_evaluations

DIMENSIONS = ("skill", "toolset", "agent", "action")


def _clean(value: object) -> str:
    return str(value or "").strip()


def _status(item: dict) -> str:
    status = _clean(item.get("status"))
    if status in {"success", "failure", "needs_adjustment"}:
        return status
    return "needs_adjustment"


def _metadata(item: dict) -> dict:
    metadata = item.get("metadata") or {}
    return metadata if isinstance(metadata, dict) else {}


def _dimension_values(item: dict, dimension: str) -> list[str]:
    metadata = _metadata(item)
    if dimension == "action":
        value = _clean(item.get("action") or "unknown")
        return [value] if value else []
    if dimension == "skill":
        skills = metadata.get("skills") or []
        if isinstance(skills, str):
            skills = [skills]
        return [_clean(value) for value in skills if _clean(value)]
    value = _clean(metadata.get(dimension))
    return [value] if value else []


def _empty_stats(name: str) -> dict:
    return {
        "name": name,
        "total": 0,
        "success": 0,
        "failure": 0,
        "needs_adjustment": 0,
        "success_rate": 0.0,
        "error_rate": 0.0,
        "utility": 0.0,
        "last_seen": 0.0,
        "recent_actions": [],
    }


def _finalize(stats: dict) -> dict:
    total = int(stats.get("total") or 0)
    success = int(stats.get("success") or 0)
    failure = int(stats.get("failure") or 0)
    adjustment = int(stats.get("needs_adjustment") or 0)
    utility = (success * 2.0) + (adjustment * 0.4) - (failure * 2.5) + log1p(total)
    stats["success_rate"] = round(success / total, 3) if total else 0.0
    stats["error_rate"] = round((failure + adjustment) / total, 3) if total else 0.0
    stats["utility"] = round(utility, 3)
    stats["recent_actions"] = list(stats.get("recent_actions") or [])[:5]
    return stats


def capability_rankings(limit: int = 8, *, path: Path | None = None) -> dict:
    items = load_task_evaluations(path).get("items") or []
    limit = max(1, int(limit))
    rankings: dict[str, list[dict]] = {dimension: [] for dimension in DIMENSIONS}
    raw_stats: dict[str, dict[str, dict]] = {dimension: {} for dimension in DIMENSIONS}

    for item in items:
        if not isinstance(item, dict):
            continue
        status = _status(item)
        action = _clean(item.get("action") or "unknown")
        seen_at = float(item.get("updated_at") or item.get("created_at") or 0.0)
        for dimension in DIMENSIONS:
            for name in _dimension_values(item, dimension):
                stats = raw_stats[dimension].setdefault(name, _empty_stats(name))
                stats["total"] += 1
                stats[status] += 1
                stats["last_seen"] = max(float(stats.get("last_seen") or 0.0), seen_at)
                recent_actions = stats.setdefault("recent_actions", [])
                if action and action not in recent_actions:
                    recent_actions.append(action)

    for dimension, values in raw_stats.items():
        rows = [_finalize(dict(stats)) for stats in values.values()]
        rows.sort(
            key=lambda value: (
                float(value.get("utility") or 0.0),
                float(value.get("success_rate") or 0.0),
                int(value.get("total") or 0),
                float(value.get("last_seen") or 0.0),
            ),
            reverse=True,
        )
        rankings[dimension] = rows[:limit]
    return rankings


def _format_rows(title: str, rows: list[dict]) -> str:
    if not rows:
        return f"{title}: sem dados suficientes."
    parts = []
    for index, item in enumerate(rows[:5], start=1):
        parts.append(
            f"{index}. {item['name']} utilidade {item['utility']}; "
            f"{item['success']} sucesso(s), {item['failure']} falha(s), "
            f"{item['needs_adjustment']} ajuste(s), uso {item['total']}"
        )
    return f"{title}: " + " | ".join(parts) + "."


def format_capability_rankings(kind: str = "all", *, limit: int = 5) -> str:
    rankings = capability_rankings(limit=limit)
    normalized = _clean(kind).lower()
    labels = {
        "skill": "Ranking de skills",
        "toolset": "Ranking de toolsets",
        "agent": "Ranking de agentes",
        "action": "Ranking de actions",
    }
    aliases = {
        "skills": "skill",
        "skill": "skill",
        "toolsets": "toolset",
        "toolset": "toolset",
        "agentes": "agent",
        "agente": "agent",
        "agents": "agent",
        "agent": "agent",
        "acoes": "action",
        "ações": "action",
        "actions": "action",
        "action": "action",
    }
    selected = aliases.get(normalized)
    if selected:
        return _format_rows(labels[selected], rankings.get(selected) or [])

    sections = [
        _format_rows(labels["agent"], rankings.get("agent") or []),
        _format_rows(labels["toolset"], rankings.get("toolset") or []),
        _format_rows(labels["skill"], rankings.get("skill") or []),
    ]
    return " ".join(sections)
