from __future__ import annotations

from actions.registry import ActionSpec, register_action
from memory.training import (
    clear_training_injuries,
    format_muscle_status_from_text,
    format_today_workout,
    format_training_status,
    mark_custom_training_from_text,
    mark_injury_from_text,
    mark_named_workout_from_text,
    mark_named_workouts_from_text,
    mark_planned_training_from_text,
    mark_training_completed,
    set_training_reminder_from_text,
    skip_today_training,
    training_snapshot,
)


def _register(name: str, description: str, handler, parameters: dict | None = None, read_only: bool = True) -> None:
    register_action(
        ActionSpec(
            name=name,
            description=description,
            handler=handler,
            category="training",
            read_only=read_only,
            parameters=parameters or {},
        )
    )


def register_training_actions() -> None:
    text_param = {"text": {"type": "string", "description": "Texto original do usuario.", "required": True}}
    _register("training.today", "Mostra o treino planejado para hoje.", lambda _args: format_today_workout())
    _register("training.status", "Mostra progresso, fadiga e lesoes do treino.", lambda _args: format_training_status())
    _register("training.snapshot", "Retorna snapshot estruturado do treino.", lambda _args: training_snapshot())
    _register(
        "training.muscle_status",
        "Consulta fadiga/lesao de grupos musculares citados.",
        lambda args: format_muscle_status_from_text(args.get("text", "")),
        text_param,
    )
    _register("training.complete_today", "Marca o treino planejado de hoje como concluido.", lambda _args: mark_training_completed(), read_only=False)
    _register("training.skip_today", "Marca o treino de hoje como pulado.", lambda _args: skip_today_training(), read_only=False)
    _register("training.register_planned", "Registra treino planejado a partir do texto.", lambda args: mark_planned_training_from_text(args.get("text", "")), text_param, read_only=False)
    _register("training.register_named", "Registra treino de um dia especifico do cronograma.", lambda args: mark_named_workout_from_text(args.get("text", "")), text_param, read_only=False)
    _register("training.register_named_many", "Registra varios treinos nomeados no mesmo texto.", lambda args: mark_named_workouts_from_text(args.get("text", "")), text_param, read_only=False)
    _register("training.register_custom", "Registra treino livre por grupos musculares.", lambda args: mark_custom_training_from_text(args.get("text", "")), text_param, read_only=False)
    _register("training.mark_injury", "Registra lesao temporaria informada no texto.", lambda args: mark_injury_from_text(args.get("text", "")), text_param, read_only=False)
    _register("training.clear_injuries", "Limpa lesoes ativas do treino.", lambda _args: clear_training_injuries(), read_only=False)
    _register("training.set_reminder", "Ajusta horario do lembrete de treino.", lambda args: set_training_reminder_from_text(args.get("text", "")), text_param, read_only=False)
