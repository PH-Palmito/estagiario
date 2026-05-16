from __future__ import annotations

from actions.registry import ActionSpec, register_action
from file_processor.processor import process_file


def _process_file(args: dict):
    return process_file(args.get("path", ""), max_chars=int(args.get("max_chars") or 4000))


def register_file_actions() -> None:
    register_action(
        ActionSpec(
            name="file.process",
            description="Detecta tipo de arquivo e extrai uma previa estruturada do conteudo.",
            handler=_process_file,
            category="files",
            read_only=True,
            parameters={
                "path": {
                    "type": "string",
                    "description": "Caminho do arquivo a processar.",
                    "required": True,
                },
                "max_chars": {
                    "type": "integer",
                    "description": "Limite de caracteres do texto extraido.",
                },
            },
        )
    )
