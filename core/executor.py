from actions import ensure_default_actions, get_action, list_actions
from core.action_errors import format_action_failure_message
from core.action_result import ActionResult, normalize_action_result
from core.command_schema import Command


class ActionInventory:
    def _names(self) -> list[str]:
        ensure_default_actions()
        return [action.name for action in list_actions()]

    def __iter__(self):
        return iter(self._names())

    def __contains__(self, name: object) -> bool:
        ensure_default_actions()
        return get_action(str(name or "")) is not None

    def __len__(self) -> int:
        return len(self._names())


ACTIONS = ActionInventory()


def execute(command: Command):
    return execute_result(command).message


def execute_result(command: Command) -> ActionResult:
    try:
        ensure_default_actions()
        spec = get_action(command.action)
        if spec:
            return normalize_action_result(spec.handler(command.params))

        return ActionResult.failed(f"Acao desconhecida: {command.action}")
    except Exception as e:
        category = ""
        try:
            spec = get_action(command.action)
            category = str(getattr(spec, "category", "") or "") if spec else ""
        except Exception:
            category = ""
        return ActionResult.failed(
            format_action_failure_message(command.action, category, e),
            error=str(e),
            data={"action": command.action, "category": category},
        )
