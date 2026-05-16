from __future__ import annotations

from actions.registry import ActionSpec, register_action
from tools.file_tools import append_file, copy_file, create_file, delete_file, move_file, rename_file, replace_in_file, write_file
from tools.folder_tools import create_folder
from tools.system_tools import close_app, run_script, type_text


def _register(name: str, description: str, handler, parameters: dict | None = None, category: str = "legacy") -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category=category,
            read_only=False,
            requires_confirmation=True,
            parameters=parameters or {},
        )
    )


def register_legacy_sensitive_actions() -> None:
    path_param = {"path": {"type": "string", "description": "Caminho do arquivo.", "required": True}}
    content_param = {"content": {"type": "string", "description": "Conteudo de texto.", "required": True}}
    src_dst_params = {
        "src": {"type": "string", "description": "Arquivo de origem.", "required": True},
        "dst": {"type": "string", "description": "Arquivo de destino.", "required": True},
    }

    _register("close_app", "Fecha um aplicativo permitido.", lambda args: close_app(args.get("target", "")), {"target": {"type": "string", "description": "Aplicativo.", "required": True}}, category="system")
    _register("run_script", "Executa um script Python permitido.", lambda args: run_script(args.get("target", "")), {"target": {"type": "string", "description": "Script Python.", "required": True}}, category="system")
    _register("type_text", "Insere texto no campo ativo.", lambda args: type_text(args.get("content", "")), content_param, category="system")
    _register("file_create", "Cria arquivo local.", lambda args: create_file(args.get("path", "")), path_param, category="files")
    _register(
        "file_write",
        "Sobrescreve arquivo local.",
        lambda args: write_file(args.get("path", ""), args.get("content", "")),
        {**path_param, **content_param},
        category="files",
    )
    _register(
        "file_append",
        "Adiciona conteudo a arquivo local.",
        lambda args: append_file(args.get("path", ""), args.get("content", "")),
        {**path_param, **content_param},
        category="files",
    )
    _register(
        "file_replace",
        "Substitui trecho em arquivo local.",
        lambda args: replace_in_file(args.get("path", ""), args.get("old_text", ""), args.get("new_text", "")),
        {
            **path_param,
            "old_text": {"type": "string", "description": "Texto antigo.", "required": True},
            "new_text": {"type": "string", "description": "Texto novo.", "required": True},
        },
        category="files",
    )
    _register("file_delete", "Remove arquivo ou pasta local.", lambda args: delete_file(args.get("path", "")), path_param, category="files")
    _register("file_copy", "Copia arquivo local.", lambda args: copy_file(args.get("src", ""), args.get("dst", "")), src_dst_params, category="files")
    _register("file_move", "Move arquivo local.", lambda args: move_file(args.get("src", ""), args.get("dst", "")), src_dst_params, category="files")
    _register(
        "file_rename",
        "Renomeia arquivo local.",
        lambda args: rename_file(args.get("src", ""), args.get("new_name", "")),
        {
            "src": {"type": "string", "description": "Arquivo de origem.", "required": True},
            "new_name": {"type": "string", "description": "Novo nome.", "required": True},
        },
        category="files",
    )
    _register("folder_create", "Cria pasta local.", lambda args: create_folder(args.get("path", "")), path_param, category="files")
