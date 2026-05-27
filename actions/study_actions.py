from __future__ import annotations

from actions.registry import ActionSpec, register_action
from memory.study import (
    add_study_goal,
    add_study_review,
    complete_study_review,
    format_study_panel,
    log_study_session,
    study_snapshot,
)


def _register(name: str, description: str, handler, parameters: dict | None = None, read_only: bool = True) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category="study",
            read_only=read_only,
            parameters=parameters or {},
        )
    )


def register_study_actions() -> None:
    text_param = {"text": {"type": "string", "description": "Texto informado pelo usuario.", "required": True}}
    index_param = {"index": {"type": "string", "description": "Numero da revisao.", "required": True}}
    _register("study.status", "Mostra metas, revisoes e progresso de estudos.", lambda _args: format_study_panel())
    _register("study.snapshot", "Retorna snapshot estruturado dos estudos.", lambda _args: study_snapshot())
    _register("study.add_goal", "Adiciona meta de estudo.", lambda args: add_study_goal(args.get("text", "")), text_param, read_only=False)
    _register("study.add_review", "Adiciona revisao de estudo.", lambda args: add_study_review(args.get("text", "")), text_param, read_only=False)
    _register("study.complete_review", "Conclui revisao pendente.", lambda args: complete_study_review(args.get("index", "1")), index_param, read_only=False)
    _register("study.log_session", "Registra sessao de estudo.", lambda args: log_study_session(args.get("text", "")), text_param, read_only=False)
