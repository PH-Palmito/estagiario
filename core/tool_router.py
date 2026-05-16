from __future__ import annotations

from typing import Any

from actions import ensure_default_actions, execute_action, list_actions


def tool_definitions(category: str | None = None) -> list[dict[str, Any]]:
    ensure_default_actions()
    return [action.tool_schema() for action in list_actions(category)]


def execute_tool(name: str, arguments: dict[str, Any] | None = None) -> Any:
    ensure_default_actions()
    return execute_action(name, arguments or {})


def tool_catalog_text(category: str | None = None) -> str:
    ensure_default_actions()
    actions = list_actions(category)
    if not actions:
        return "Nenhuma action registrada."
    lines = []
    for action in actions:
        mode = "leitura" if action.read_only else "escrita"
        lines.append(f"- {action.name} [{action.category}, {mode}]: {action.description}")
    return "\n".join(lines)
