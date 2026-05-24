from actions import ensure_default_actions, get_action, list_actions
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
    try:
        ensure_default_actions()
        spec = get_action(command.action)
        if spec:
            return spec.handler(command.params)

        return f"Ação desconhecida: {command.action}"
    except Exception as e:
        return f"Erro ao executar {command.action}: {e}"
