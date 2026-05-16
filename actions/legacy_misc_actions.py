from __future__ import annotations

from actions.registry import ActionSpec, register_action
from core.normalizer import normalize_action
from memory.ui_state import update_ui_state
from tools.code_tools import inspect_code_target, inspect_selected_code, inspect_workspace_code
from tools.smart_open_tools import (
    close_smart_target,
    forget_smart_memory,
    open_smart_target,
    open_smart_target_as_kind,
    remember_target_kind,
)
from tools.system_tools import disable_windows_startup, enable_windows_startup
from tools.web_tools import google_search, open_chatgpt


def _register(
    name: str,
    description: str,
    handler,
    parameters: dict | None = None,
    category: str = "misc",
    read_only: bool = True,
    requires_confirmation: bool = False,
) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category=category,
            read_only=read_only,
            requires_confirmation=requires_confirmation,
            parameters=parameters or {},
        )
    )


def _run_macro(args: dict) -> str:
    from core.executor import execute

    results = []
    for step in args.get("steps") or []:
        try:
            command = normalize_action(step) if isinstance(step, dict) else step
            results.append(execute(command))
        except Exception as exc:
            results.append(f"Erro em macro: {exc}")
    return "\n".join(str(item) for item in results)


def _ui_show_map(args: dict) -> str:
    raw_target = args.get("target")
    target = raw_target if isinstance(raw_target, dict) else {"location": str(raw_target or "").strip()}
    update_ui_state(
        {
            "visible": True,
            "map_panel_open": True,
            "map_request": target,
            "last_command": "mostrar mapa",
        }
    )
    label = str(target.get("label") or target.get("location") or target.get("destination") or "mapa").strip()
    return f"Mapa aberto na interface: {label}."


def register_legacy_misc_actions() -> None:
    target_param = {"target": {"type": "string", "description": "Alvo.", "required": True}}
    query_param = {"query": {"type": "string", "description": "Busca.", "required": True}}

    _register("start_conversation", "Inicia modo conversa.", lambda _args: "Modo conversa ativado.", category="conversation")
    _register("stop_conversation", "Encerra modo conversa.", lambda _args: "Modo conversa encerrado.", category="conversation")
    _register("respond", "Retorna uma mensagem direta.", lambda args: args.get("message", ""), {"message": {"type": "string", "required": True}}, category="conversation")
    _register("run_macro", "Executa uma macro de comandos.", _run_macro, {"steps": {"type": "array", "required": True}}, category="automation", read_only=False, requires_confirmation=True)
    _register("ui_show_map", "Mostra mapa na interface.", _ui_show_map, {"target": {"type": "object", "required": True}}, category="ui")
    _register("web_google_search", "Pesquisa no Google.", lambda args: google_search(args.get("query", "")), query_param, category="web", read_only=False)
    _register("web_open_chatgpt", "Abre ChatGPT.", lambda _args: open_chatgpt(), category="web", read_only=False)
    _register("code_inspect_workspace", "Inspeciona codigo do workspace.", lambda _args: inspect_workspace_code(), category="code")
    _register("code_inspect_target", "Inspeciona codigo de um alvo.", lambda args: inspect_code_target(args.get("target")), {"target": {"type": "string", "description": "Arquivo ou pasta."}}, category="code")
    _register("code_inspect_selection", "Inspeciona codigo selecionado.", lambda _args: inspect_selected_code(), category="code")
    _register("smart_open", "Abre app ou site por memoria inteligente.", lambda args: open_smart_target(args.get("target", "")), target_param, category="system", read_only=False)
    _register(
        "smart_open_choice",
        "Abre alvo inteligente como app ou site.",
        lambda args: open_smart_target_as_kind(args.get("target", ""), args.get("kind", "")),
        {**target_param, "kind": {"type": "string", "description": "app ou site.", "required": True}},
        category="system",
        read_only=False,
    )
    _register("remember_target_kind", "Memoriza alvo como app ou site.", lambda args: remember_target_kind(args.get("target", ""), args.get("kind", "")), {**target_param, "kind": {"type": "string", "required": True}}, category="system", read_only=False, requires_confirmation=True)
    _register("forget_smart_memory", "Esquece app/site aprendido.", lambda args: forget_smart_memory(args.get("target", "")), target_param, category="system", read_only=False, requires_confirmation=True)
    _register("smart_close_app", "Fecha app por memoria inteligente.", lambda args: close_smart_target(args.get("target", "")), target_param, category="system", read_only=False, requires_confirmation=True)
    _register("windows_startup_enable", "Ativa inicializacao com Windows.", lambda _args: enable_windows_startup(), category="system", read_only=False, requires_confirmation=True)
    _register("windows_startup_disable", "Desativa inicializacao com Windows.", lambda _args: disable_windows_startup(), category="system", read_only=False, requires_confirmation=True)
