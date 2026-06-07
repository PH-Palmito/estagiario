from __future__ import annotations

import json
from typing import Any

from actions import ensure_default_actions, execute_action_result, get_action, list_actions


def _safe_json_loads(raw: str) -> tuple[dict[str, Any], str]:
    text = str(raw or "").strip()
    if not text:
        return {}, ""
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, f"JSON invalido: {exc.msg}"
    if not isinstance(payload, dict):
        return {}, "JSON de argumentos precisa ser um objeto."
    return payload, ""


def action_rpc_catalog(category: str | None = None) -> dict:
    ensure_default_actions()
    actions = list_actions(category)
    return {
        "ok": True,
        "actions": [
            {
                "name": action.name,
                "description": action.description,
                "category": action.category,
                "read_only": action.read_only,
                "requires_confirmation": action.requires_confirmation,
            }
            for action in actions
        ],
    }


def action_rpc_schema(name: str) -> dict:
    ensure_default_actions()
    spec = get_action(name)
    if not spec:
        return {"ok": False, "error": f"Action desconhecida: {name}"}
    return {"ok": True, "schema": spec.tool_schema()}


def action_rpc_execute(name: str, arguments: dict | None = None, *, allow_write: bool = False) -> dict:
    ensure_default_actions()
    action_name = str(name or "").strip()
    spec = get_action(action_name)
    if not spec:
        return {"ok": False, "action": action_name, "error": f"Action desconhecida: {action_name}"}
    if (not spec.read_only or spec.requires_confirmation) and not allow_write:
        return {
            "ok": False,
            "action": action_name,
            "error": "Action bloqueada pelo RPC local: use --allow-write somente em scripts confiaveis.",
            "metadata": {
                "category": spec.category,
                "read_only": spec.read_only,
                "requires_confirmation": spec.requires_confirmation,
            },
        }

    result = execute_action_result(action_name, arguments or {})
    return {
        "ok": bool(result.success),
        "action": action_name,
        "message": result.message,
        "error": result.error,
        "data": result.data,
        "metadata": {
            "category": spec.category,
            "read_only": spec.read_only,
            "requires_confirmation": spec.requires_confirmation,
        },
    }


def action_rpc_execute_json(name: str, raw_arguments: str = "", *, allow_write: bool = False) -> dict:
    arguments, error = _safe_json_loads(raw_arguments)
    if error:
        return {"ok": False, "action": str(name or "").strip(), "error": error}
    return action_rpc_execute(name, arguments, allow_write=allow_write)


def format_action_rpc_payload(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
