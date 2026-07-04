from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import unicodedata

from core.conversation_reply import conversation_reply
from core.router_registry import (
    INTENT_LEVEL_COMPOSITE_TASK,
    INTENT_LEVEL_DIRECT_COMMAND,
    INTENT_LEVEL_QUESTION,
)
from core.voice_modes import (
    format_dictation_text,
    is_conversation_stop,
    is_dictation_start,
    is_dictation_stop,
)


@dataclass(frozen=True)
class InteractiveModesState:
    dictation_mode: bool
    dictation_ready_announced: bool
    conversation_mode: bool
    conversation_ready_announced: bool


@dataclass(frozen=True)
class InteractiveModesResult:
    handled: bool
    state: InteractiveModesState
    message: str = ""
    voice_mode: bool | None = None


def _conversation_input_should_route(user_input: str) -> bool:
    """Let clear commands leave conversation mode without turning it off."""
    normalized = unicodedata.normalize("NFD", user_input.lower())
    normalized = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    compact = " ".join(normalized.replace(",", " ").replace(".", " ").split())
    if compact in {
        "bom dia",
        "boa tarde",
        "boa noite",
        "oi",
        "ola",
        "olá",
        "e ai",
        "eae",
        "tudo bem",
    }:
        return False

    try:
        from core.router import route_match

        match = route_match(user_input)
    except Exception:
        return False

    if not match:
        return False

    if match.group_name in {"conversation", "general_questions"}:
        return False

    return match.intent_level in {
        INTENT_LEVEL_DIRECT_COMMAND,
        INTENT_LEVEL_COMPOSITE_TASK,
        INTENT_LEVEL_QUESTION,
    }


def handle_interactive_modes(
    user_input: str,
    state: InteractiveModesState,
    *,
    voice_mode: bool,
    hotword_mode: bool,
    hotkey_name: str,
    waiting_for_direct_response: Callable[[], bool],
    set_voice_status: Callable[[str], None],
    type_text: Callable[[str], str],
    chat_response: Callable[[str], str],
) -> InteractiveModesResult:
    if is_dictation_stop(user_input):
        next_state = InteractiveModesState(
            dictation_mode=False,
            dictation_ready_announced=False,
            conversation_mode=state.conversation_mode,
            conversation_ready_announced=state.conversation_ready_announced,
        )
        if hotword_mode and not state.conversation_mode:
            set_voice_status(f"BOTAO {hotkey_name}")
        return InteractiveModesResult(True, next_state, "Modo ditado encerrado.", voice_mode)

    if state.dictation_mode:
        result = type_text(format_dictation_text(user_input))
        if result != "Texto inserido no campo ativo.":
            return InteractiveModesResult(True, state, result, False)
        return InteractiveModesResult(True, state)

    if is_dictation_start(user_input):
        next_state = InteractiveModesState(
            dictation_mode=True,
            dictation_ready_announced=False,
            conversation_mode=False,
            conversation_ready_announced=False,
        )
        if hotword_mode:
            set_voice_status("DITADO")
        return InteractiveModesResult(
            True,
            next_state,
            "Modo ditado ativado. Pode falar sem apertar F8. Para sair, diga parar ditado.",
            voice_mode,
        )

    if state.conversation_mode and is_conversation_stop(user_input):
        next_state = InteractiveModesState(
            dictation_mode=state.dictation_mode,
            dictation_ready_announced=state.dictation_ready_announced,
            conversation_mode=False,
            conversation_ready_announced=False,
        )
        if hotword_mode:
            set_voice_status(f"BOTAO {hotkey_name}")
        return InteractiveModesResult(True, next_state, "Modo conversa encerrado. Voltei para comandos.", voice_mode)

    if state.conversation_mode and not waiting_for_direct_response():
        if _conversation_input_should_route(user_input):
            return InteractiveModesResult(False, state)
        return InteractiveModesResult(True, state, conversation_reply(user_input, chat_response), voice_mode)

    return InteractiveModesResult(False, state)
