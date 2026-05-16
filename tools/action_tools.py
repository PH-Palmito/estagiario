from __future__ import annotations

import json
from typing import Any

from core.tool_router import execute_tool, tool_catalog_text, tool_definitions
from file_processor.processor import process_file
from memory.action_memory import list_memory_entries, recall_memory, remember_memory


def _format_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, indent=2)


def action_tool_list(category: str | None = None) -> str:
    return tool_catalog_text(category or None)


def action_tool_schema(category: str | None = None) -> str:
    return _format_result(tool_definitions(category or None))


def action_tool_execute(name: str, arguments: dict | None = None) -> str:
    return _format_result(execute_tool(name, arguments or {}))


def action_file_process(path: str) -> str:
    return _format_result(process_file(path))


def action_memory_remember(namespace: str, key: str, value: Any) -> str:
    return _format_result(remember_memory(namespace, key, value))


def action_memory_recall(namespace: str, key: str) -> str:
    return _format_result(recall_memory(namespace, key))


def action_memory_list(namespace: str) -> str:
    return _format_result(list_memory_entries(namespace))
