from __future__ import annotations

from actions.registry import ActionSpec, register_action
from tools.image_tools import (
    analyze_browser_image,
    analyze_clipboard_image,
    analyze_graph_target,
    analyze_image_target,
    analyze_screen_graph,
    analyze_screen_image,
)
from tools.vision_tools import answer_visual_question_with_context_memory, start_light_vision_model_download, vision_install_hint


def _execute_registered_action(args: dict):
    from core.tool_router import execute_tool

    name = str(args.get("name") or "").strip()
    if name == "action_tool_execute":
        return "Nao executo action_tool_execute chamando ele mesmo."
    return execute_tool(name, args.get("arguments") or {})


def _register(
    name: str,
    description: str,
    handler,
    parameters: dict | None = None,
    read_only: bool = True,
    requires_confirmation: bool = False,
) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category="vision",
            read_only=read_only,
            requires_confirmation=requires_confirmation,
            parameters=parameters or {},
        )
    )


def register_legacy_vision_actions() -> None:
    _register("image_analyze", "Analisa imagem por caminho.", lambda args: analyze_image_target(args.get("target")), {"target": {"type": "string", "description": "Caminho da imagem."}})
    _register("image_analyze_graph", "Analisa grafico por caminho.", lambda args: analyze_graph_target(args.get("target")), {"target": {"type": "string", "description": "Caminho da imagem."}})
    _register("image_analyze_screen", "Analisa imagem da tela.", lambda _args: analyze_screen_image())
    _register("image_analyze_screen_graph", "Analisa grafico na tela.", lambda _args: analyze_screen_graph())
    _register("image_analyze_browser", "Analisa imagem do navegador.", lambda _args: analyze_browser_image())
    _register("image_analyze_clipboard", "Analisa imagem copiada.", lambda _args: analyze_clipboard_image())
    _register(
        "vision_answer_question",
        "Responde pergunta visual usando memoria/contexto.",
        lambda args: answer_visual_question_with_context_memory(args.get("question", "")),
        {"question": {"type": "string", "description": "Pergunta visual.", "required": True}},
    )
    _register("vision_install_hint", "Mostra instrucoes para instalar visao.", lambda _args: vision_install_hint())
    _register(
        "vision_download_light_model",
        "Baixa modelo visual leve.",
        lambda _args: start_light_vision_model_download(),
        read_only=False,
        requires_confirmation=True,
    )
    _register(
        "action_tool_execute",
        "Executa uma action registrada pelo catalogo.",
        _execute_registered_action,
        {
            "name": {"type": "string", "description": "Nome da action.", "required": True},
            "arguments": {"type": "object", "description": "Argumentos da action."},
        },
        read_only=False,
        requires_confirmation=True,
    )
