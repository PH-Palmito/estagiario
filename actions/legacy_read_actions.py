from __future__ import annotations

import json

from actions.registry import ActionSpec, list_actions, register_action
from file_processor.processor import process_file
from memory.action_memory import list_memory_entries, recall_memory
from memory.agenda import list_agenda_all, list_agenda_today, list_agenda_tomorrow
from memory.reminders import list_reminders
from memory.vision_history import format_vision_history
from services import briefing_service, investment_service, vision_service
from tools.bluetooth_tools import bluetooth_status
from tools.file_tools import list_files, read_file
from tools.smart_open_tools import list_smart_memory
from tools.system_tools import windows_startup_status
from tools.weather_tools import weather_summary


def _format_result(result) -> str:
    if isinstance(result, str):
        return result
    return json.dumps(result, ensure_ascii=False, indent=2)


def _format_memory_recall_result(result: dict) -> str:
    if not result.get("ok"):
        return str(result.get("error") or "Memoria nao encontrada.")
    item = result.get("item") or {}
    return f"Memoria {result.get('namespace', 'general')}/{result.get('key', '')}: {item.get('value', '')}."


def _format_memory_list_result(result: dict) -> str:
    namespace = result.get("namespace", "general")
    keys = result.get("keys") or []
    if not keys:
        return f"Nao ha memorias salvas em {namespace}."
    return f"Memorias em {namespace}: " + "; ".join(str(key) for key in keys) + "."


def _tool_catalog_text(category: str | None = None) -> str:
    actions = list_actions(category)
    if not actions:
        return "Nenhuma action registrada."
    lines = []
    for action in actions:
        mode = "leitura" if action.read_only else "escrita"
        lines.append(f"- {action.name} [{action.category}, {mode}]: {action.description}")
    return "\n".join(lines)


def _tool_definitions(category: str | None = None) -> list[dict]:
    return [action.tool_schema() for action in list_actions(category)]


def _register(
    name: str,
    description: str,
    handler,
    parameters: dict | None = None,
    category: str = "legacy",
) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category=category,
            read_only=True,
            parameters=parameters or {},
        )
    )


def register_legacy_read_actions() -> None:
    _register("daily_briefing", "Gera o briefing diario curto.", lambda _args: briefing_service.daily_briefing(), category="briefing")
    _register("daily_routine", "Gera a rotina diaria acionavel.", lambda _args: briefing_service.daily_routine(), category="briefing")
    _register(
        "weather_summary",
        "Consulta resumo de clima para uma localidade.",
        lambda args: weather_summary(args.get("location")),
        {"location": {"type": "string", "description": "Cidade ou localidade."}},
        category="weather",
    )
    _register(
        "windows_startup_status",
        "Mostra se o Axel esta configurado para iniciar com o Windows.",
        lambda _args: windows_startup_status(),
        category="system",
    )
    _register("list_smart_memory", "Lista atalhos inteligentes salvos.", lambda _args: list_smart_memory(), category="system")
    _register("reminder_list", "Lista lembretes pendentes.", lambda _args: list_reminders(), category="agenda")
    _register("agenda_list_today", "Lista agenda de hoje.", lambda _args: list_agenda_today(), category="agenda")
    _register("agenda_list_tomorrow", "Lista agenda de amanha.", lambda _args: list_agenda_tomorrow(), category="agenda")
    _register("agenda_list_all", "Lista toda a agenda salva.", lambda _args: list_agenda_all(), category="agenda")
    _register(
        "investment_memory_answer",
        "Responde pergunta usando memoria local de investimentos.",
        lambda args: investment_service.investment_answer(args.get("question", "")),
        {"question": {"type": "string", "description": "Pergunta sobre investimentos.", "required": True}},
        category="investments",
    )
    _register("investment_memory_summary", "Resume a carteira salva.", lambda _args: investment_service.investment_summary(), category="investments")
    _register("investment_financial_report", "Gera relatorio financeiro da carteira.", lambda _args: investment_service.investment_report(), category="investments")
    _register("investment_portfolio_monitor", "Executa monitor proativo local da carteira.", lambda _args: investment_service.investment_monitor(), category="investments")
    _register("investment_memory_status", "Mostra status da memoria de investimentos.", lambda _args: investment_service.investment_status(), category="investments")
    _register("investment_list_watchlist", "Lista watchlist de investimentos.", lambda _args: investment_service.list_watchlist(), category="investments")
    _register(
        "investment_get_auto_ceiling_settings",
        "Mostra configuracao de preco-teto automatico.",
        lambda _args: investment_service.get_auto_ceiling_settings(),
        category="investments",
    )
    _register("bluetooth_status", "Mostra status do Bluetooth.", lambda _args: bluetooth_status(), category="system")
    _register("vision_status", "Mostra status do modelo visual.", lambda _args: vision_service.vision_status(), category="vision")
    _register("vision_active_model", "Mostra o modelo visual ativo.", lambda _args: vision_service.active_vision_model(), category="vision")
    _register("vision_last_analysis", "Mostra a ultima analise visual salva.", lambda _args: vision_service.last_visual_analysis(), category="vision")
    _register("vision_history", "Mostra historico visual recente.", lambda _args: format_vision_history(), category="vision")
    _register("list_files", "Lista arquivos de uma pasta.", lambda args: list_files(args.get("path", "")), category="files")
    _register(
        "file_read",
        "Le um arquivo local.",
        lambda args: read_file(args.get("path", "")),
        {"path": {"type": "string", "description": "Caminho do arquivo.", "required": True}},
        category="files",
    )
    _register("action_tool_list", "Lista actions registradas.", lambda args: _tool_catalog_text(args.get("category") or None), category="actions")
    _register("action_tool_schema", "Mostra schemas das actions registradas.", lambda args: _format_result(_tool_definitions(args.get("category") or None)), category="actions")
    _register(
        "action_file_process",
        "Detecta tipo de arquivo e extrai uma previa estruturada.",
        lambda args: _format_result(process_file(args.get("path", ""))),
        {"path": {"type": "string", "description": "Caminho do arquivo.", "required": True}},
        category="files",
    )
    _register(
        "action_memory_recall",
        "Busca memoria simples em namespace local.",
        lambda args: _format_memory_recall_result(recall_memory(args.get("namespace", "general"), args.get("key", ""))),
        {
            "namespace": {"type": "string", "description": "Area da memoria."},
            "key": {"type": "string", "description": "Chave da memoria.", "required": True},
        },
        category="memory",
    )
    _register(
        "action_memory_list",
        "Lista memorias simples de um namespace local.",
        lambda args: _format_memory_list_result(list_memory_entries(args.get("namespace", "general"))),
        {"namespace": {"type": "string", "description": "Area da memoria."}},
        category="memory",
    )
