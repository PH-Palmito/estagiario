from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


ActionHandler = Callable[[dict[str, Any]], Any]


@dataclass(frozen=True)
class ActionSpec:
    name: str
    description: str
    handler: ActionHandler
    parameters: dict[str, dict[str, Any]] = field(default_factory=dict)
    category: str = "general"
    read_only: bool = True
    requires_confirmation: bool = False

    def tool_schema(self) -> dict[str, Any]:
        required = [
            name
            for name, spec in self.parameters.items()
            if spec.get("required", False)
        ]
        properties = {
            name: {
                "type": spec.get("type", "string"),
                "description": spec.get("description", ""),
            }
            for name, spec in self.parameters.items()
        }
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
            "metadata": {
                "category": self.category,
                "read_only": self.read_only,
                "requires_confirmation": self.requires_confirmation,
            },
        }


_ACTIONS: dict[str, ActionSpec] = {}


def register_action(spec: ActionSpec) -> ActionSpec:
    if not spec.name:
        raise ValueError("Action name is required.")
    _ACTIONS[spec.name] = spec
    return spec


def get_action(name: str) -> ActionSpec | None:
    return _ACTIONS.get(str(name or "").strip())


def list_actions(category: str | None = None) -> list[ActionSpec]:
    actions = list(_ACTIONS.values())
    if category:
        actions = [action for action in actions if action.category == category]
    return sorted(actions, key=lambda action: action.name)


def execute_action(name: str, arguments: dict[str, Any] | None = None) -> Any:
    spec = get_action(name)
    if not spec:
        available = ", ".join(action.name for action in list_actions())
        return f"Action desconhecida: {name}. Disponiveis: {available}"
    return spec.handler(arguments or {})
