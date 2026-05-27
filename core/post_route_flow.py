from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass

from core.command_schema import Command
from core.permission_policy import command_requires_confirmation


@dataclass(frozen=True)
class PostRouteState:
    pending_command: Command | None
    pending_command_learning_text: str
    pending_smart_open_choice: str | None
    pending_smart_open_invalid_attempts: int
    direct_response_ready_announced: bool
    conversation_mode: bool
    conversation_ready_announced: bool


@dataclass(frozen=True)
class PostRouteResult:
    handled: bool
    state: PostRouteState
    message: str = ""


def handle_post_route_action(
    raw_action: dict,
    *,
    user_input: str,
    original_user_input: str,
    voice_mode: bool,
    state: PostRouteState,
    last_command: Command | None,
    process_action: Callable[[dict], Command | str],
    execute_command: Callable[[Command], str],
    execute_routine_steps: Callable[[object], str],
    clear_chat_history: Callable[[], None],
    confirmation_prompt: Callable[[Command], str],
    smart_open_needs_choice: Callable[[str | None], bool],
    show_map_in_ui: Callable[[dict | None], str],
    update_runtime_state: Callable[[Command, str], None],
    is_unclear_response: Callable[[object], bool],
    maybe_suggest_probable_command: Callable[[str], dict | None],
) -> PostRouteResult:
    if voice_mode and is_unclear_response(raw_action):
        suggestion = maybe_suggest_probable_command(user_input)
        if suggestion:
            processed = process_action(suggestion["action"])
            if not isinstance(processed, str):
                return PostRouteResult(
                    handled=True,
                    state=PostRouteState(
                        pending_command=processed,
                        pending_command_learning_text=original_user_input,
                        pending_smart_open_choice=state.pending_smart_open_choice,
                        pending_smart_open_invalid_attempts=state.pending_smart_open_invalid_attempts,
                        direct_response_ready_announced=False,
                        conversation_mode=state.conversation_mode,
                        conversation_ready_announced=state.conversation_ready_announced,
                    ),
                    message=suggestion["question"],
                )

    intent = raw_action.get("intent")
    if intent == "run_routine":
        return PostRouteResult(True, state, execute_routine_steps(raw_action.get("target")))

    if intent == "start_conversation":
        clear_chat_history()
        return PostRouteResult(
            True,
            PostRouteState(
                pending_command=state.pending_command,
                pending_command_learning_text=state.pending_command_learning_text,
                pending_smart_open_choice=state.pending_smart_open_choice,
                pending_smart_open_invalid_attempts=state.pending_smart_open_invalid_attempts,
                direct_response_ready_announced=state.direct_response_ready_announced,
                conversation_mode=True,
                conversation_ready_announced=False,
            ),
            "Modo conversa ativado. Pode falar sem apertar F8. Para sair, diga parar conversa.",
        )

    if intent == "stop_conversation":
        return PostRouteResult(
            True,
            PostRouteState(
                pending_command=state.pending_command,
                pending_command_learning_text=state.pending_command_learning_text,
                pending_smart_open_choice=state.pending_smart_open_choice,
                pending_smart_open_invalid_attempts=state.pending_smart_open_invalid_attempts,
                direct_response_ready_announced=state.direct_response_ready_announced,
                conversation_mode=False,
                conversation_ready_announced=False,
            ),
            "Modo conversa encerrado. Voltei para comandos.",
        )

    if intent == "repeat_last":
        if last_command is None:
            return PostRouteResult(True, state, "Nada para repetir.")
        return PostRouteResult(True, state, execute_command(deepcopy(last_command)))

    processed = process_action(raw_action)
    if isinstance(processed, str):
        return PostRouteResult(True, state, processed)

    if processed.action == "smart_open" and smart_open_needs_choice(processed.params.get("target")):
        target = processed.params.get("target")
        return PostRouteResult(
            True,
            PostRouteState(
                pending_command=state.pending_command,
                pending_command_learning_text=state.pending_command_learning_text,
                pending_smart_open_choice=target,
                pending_smart_open_invalid_attempts=0,
                direct_response_ready_announced=False,
                conversation_mode=state.conversation_mode,
                conversation_ready_announced=state.conversation_ready_announced,
            ),
            f"Primeira vez que vejo {target}. Quer abrir como app ou site?",
        )

    if processed.action == "ui_show_map":
        result = show_map_in_ui(processed.params.get("target"))
        update_runtime_state(processed, result)
        return PostRouteResult(True, state, result)

    if command_requires_confirmation(processed):
        return PostRouteResult(
            True,
            PostRouteState(
                pending_command=processed,
                pending_command_learning_text="",
                pending_smart_open_choice=state.pending_smart_open_choice,
                pending_smart_open_invalid_attempts=state.pending_smart_open_invalid_attempts,
                direct_response_ready_announced=False,
                conversation_mode=state.conversation_mode,
                conversation_ready_announced=state.conversation_ready_announced,
            ),
            confirmation_prompt(processed),
        )

    return PostRouteResult(True, state, execute_command(processed))
