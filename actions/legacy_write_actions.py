from __future__ import annotations

import json

from actions.registry import ActionSpec, register_action
from memory.action_memory import remember_memory
from memory.agenda import add_agenda_item, remove_agenda_item
from memory.reminders import add_reminder, remove_reminder


def _format_result(result) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, indent=2)


def _format_memory_remember_result(result: dict) -> str:
    if not result.get("ok"):
        return str(result.get("error") or "Nao consegui salvar essa memoria.")
    return f"Memoria salva em {result.get('namespace', 'general')}: {result.get('key', 'nota')}."


def _register(
    name: str,
    description: str,
    handler,
    parameters: dict | None = None,
    category: str = "legacy",
    requires_confirmation: bool = True,
) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category=category,
            read_only=False,
            requires_confirmation=requires_confirmation,
            parameters=parameters or {},
        )
    )


def register_legacy_write_actions() -> None:
    text_param = {"text": {"type": "string", "description": "Texto informado pelo usuario.", "required": True}}
    index_param = {"index": {"type": "string", "description": "Numero do item.", "required": True}}

    _register("agenda_add", "Adiciona compromisso na agenda local.", lambda args: add_agenda_item(args.get("text", "")), text_param, category="agenda")
    _register(
        "agenda_remove",
        "Remove compromisso da agenda local.",
        lambda args: remove_agenda_item(args.get("index", ""), args.get("scope", "today")),
        {
            **index_param,
            "scope": {"type": "string", "description": "Escopo da agenda: today ou tomorrow."},
        },
        category="agenda",
    )
    _register("reminder_add", "Adiciona lembrete local.", lambda args: add_reminder(args.get("text", "")), text_param, category="agenda")
    _register("reminder_remove", "Remove lembrete local.", lambda args: remove_reminder(args.get("index", "")), index_param, category="agenda")
    _register(
        "action_memory_remember",
        "Salva memoria simples em namespace local.",
        lambda args: _format_memory_remember_result(remember_memory(args.get("namespace", "general"), args.get("key", ""), args.get("value"))),
        {
            "namespace": {"type": "string", "description": "Area da memoria."},
            "key": {"type": "string", "description": "Chave da memoria.", "required": True},
            "value": {"type": "string", "description": "Valor a salvar.", "required": True},
        },
        category="memory",
    )
