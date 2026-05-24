from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from core.command_schema import Command
from core.router_macros import detect_create_macro_start


@dataclass(frozen=True)
class MacroRecordingState:
    creating_macro: bool
    macro_name: str | None
    macro_steps: list[dict]


@dataclass(frozen=True)
class MacroRecordingResult:
    handled: bool
    state: MacroRecordingState
    message: str = ""


def handle_macro_recording(
    user_input: str,
    state: MacroRecordingState,
    *,
    route: Callable[[str], dict],
    process_action: Callable[[dict], Command | str],
    add_macro: Callable[[str, list[dict]], None],
) -> MacroRecordingResult:
    if state.creating_macro:
        macro_name = state.macro_name or ""

        if user_input.lower().strip() == "fim":
            add_macro(macro_name, state.macro_steps)
            return MacroRecordingResult(
                handled=True,
                state=MacroRecordingState(False, None, []),
                message=f"Macro '{macro_name}' criada com {len(state.macro_steps)} passos.",
            )

        raw_action = route(user_input)
        if raw_action.get("intent") in {"start_macro", "run_macro", "run_routine"}:
            return MacroRecordingResult(
                handled=True,
                state=state,
                message="Esse comando nao pode ser adicionado dentro da macro.",
            )

        processed = process_action(raw_action)
        if isinstance(processed, str):
            return MacroRecordingResult(
                handled=True,
                state=state,
                message=f"Passo invalido: {processed}",
            )

        return MacroRecordingResult(
            handled=True,
            state=MacroRecordingState(True, macro_name, [*state.macro_steps, raw_action]),
            message="Passo adicionado.",
        )

    start_macro = detect_create_macro_start(user_input)
    if start_macro:
        macro_name = start_macro["target"]
        return MacroRecordingResult(
            handled=True,
            state=MacroRecordingState(True, macro_name, []),
            message=f"Criando macro '{macro_name}'. Digite ou fale comandos e finalize com 'fim'.",
        )

    return MacroRecordingResult(handled=False, state=state)
