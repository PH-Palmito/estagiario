from core.command_schema import Command


def _registered_spec(name: str):
    try:
        from actions import ensure_default_actions, get_action
    except Exception:
        return None

    ensure_default_actions()
    return get_action(name)


def _missing_field_message(field: str) -> str:
    messages = {
        "path": "Qual arquivo?",
        "src": "Qual arquivo de origem?",
        "dst": "Qual destino?",
        "new_name": "Qual o novo nome?",
        "query": "Qual pesquisa?",
        "target": "Qual alvo?",
        "content": "Qual texto?",
        "text": "Qual compromisso devo registrar?",
        "location": "Qual lugar devo consultar?",
        "vibe": "Qual clima ou genero musical?",
        "index": "Qual item?",
        "kind": "Isso e app ou site?",
        "site": "Qual site?",
        "service": "Qual servico?",
        "question": "Qual pergunta?",
        "steps": "A macro esta vazia.",
        "ticker": "Qual ticker?",
        "price": "Qual preco?",
        "value": "Qual valor?",
        "thesis": "Qual tese?",
        "name": "Qual action?",
    }
    return messages.get(field, f"Parametro obrigatorio ausente: {field}")


def _required_fields_from_spec(parameters: dict | None) -> list[str]:
    return [
        name
        for name, spec in (parameters or {}).items()
        if isinstance(spec, dict) and spec.get("required")
    ]


def _validate_required_fields(params: dict, required: list[str]):
    for field in required:
        if params.get(field) in (None, "", []):
            return False, _missing_field_message(field)
    return True, None


def _validate_registered_action_tool(command: Command):
    if command.action != "action_tool_execute":
        return True, None

    name = str(command.params.get("name") or "").strip()
    spec = _registered_spec(name)
    if not spec:
        return False, f"Action registrada nao encontrada: {name}"

    arguments = command.params.get("arguments") or {}
    if not isinstance(arguments, dict):
        return False, "Argumentos da action precisam ser um objeto."

    missing = [
        field
        for field in _required_fields_from_spec(spec.parameters)
        if arguments.get(field) in (None, "", [])
    ]
    if missing:
        return False, "Parametro obrigatorio da action ausente: " + ", ".join(missing)

    return True, None


def validate_command(command: Command):
    spec = _registered_spec(command.action)
    if not spec:
        return False, f"Action registrada nao encontrada: {command.action}"

    ok, error = _validate_required_fields(
        command.params,
        _required_fields_from_spec(spec.parameters),
    )
    if not ok:
        return ok, error

    ok, error = _validate_registered_action_tool(command)
    if not ok:
        return ok, error

    return True, None
