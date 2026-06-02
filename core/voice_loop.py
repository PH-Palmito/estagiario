from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


PANEL_INLINE_PREFIX = "\0panel:"


@dataclass(frozen=True)
class ListenModes:
    direct_response: bool
    conversation: bool
    dictation: bool

    @property
    def any_modal(self) -> bool:
        return self.direct_response or self.conversation or self.dictation


@dataclass(frozen=True)
class VoiceReadState:
    voice_mode: bool
    hotword_mode: bool
    voice_paused: bool
    direct_response_ready_announced: bool
    conversation_ready_announced: bool
    dictation_ready_announced: bool
    conversation_mode: bool
    dictation_mode: bool
    pending_command: object | None = None
    pending_smart_open_choice: object | None = None


@dataclass(frozen=True)
class VoiceReadResult:
    user_input: str
    queued_user_input: str
    inline_command: str
    voice_paused: bool
    should_continue: bool
    modes: ListenModes
    direct_response_ready_announced: bool
    conversation_ready_announced: bool
    dictation_ready_announced: bool
    repeat_listen_until: float | None = None


@dataclass(frozen=True)
class VoiceStopDecision:
    should_stop: bool
    message: str = ""
    voice_mode: bool = False


@dataclass(frozen=True)
class VoiceInputCycleResult:
    user_input: str
    queued_user_input: str
    voice_paused: bool
    should_break: bool
    break_message: str = ""
    break_voice_mode: bool = False
    direct_response_ready_announced: bool = False
    conversation_ready_announced: bool = False
    dictation_ready_announced: bool = False
    repeat_listen_until: float | None = None
    hotword_ui_enabled: bool | None = None
    clear_status_line: bool = False


def determine_listen_modes(
    *,
    voice_mode: bool,
    hotword_mode: bool,
    voice_paused: bool,
    waiting_for_direct_response: bool,
    conversation_mode: bool,
    dictation_mode: bool,
) -> ListenModes:
    direct_response = (
        voice_mode
        and hotword_mode
        and not voice_paused
        and waiting_for_direct_response
    )
    conversation = (
        voice_mode
        and hotword_mode
        and not voice_paused
        and conversation_mode
        and not direct_response
    )
    dictation = (
        voice_mode
        and hotword_mode
        and not voice_paused
        and dictation_mode
        and not direct_response
        and not conversation_mode
    )
    return ListenModes(
        direct_response=direct_response,
        conversation=conversation,
        dictation=dictation,
    )


def should_use_inline_hotword_command(
    *,
    modes: ListenModes,
    voice_mode: bool,
    hotword_mode: bool,
    inline_command: str,
) -> bool:
    return bool(not modes.any_modal and voice_mode and hotword_mode and inline_command)


def should_read_default_input(
    *,
    queued_user_input: str,
    modes: ListenModes,
) -> bool:
    return bool(not queued_user_input and not modes.any_modal)


def stop_decision_from_user_input(user_input: str, voice_mode: bool) -> VoiceStopDecision:
    normalized = str(user_input or "").strip().lower()
    if normalized in {"sair", "exit"}:
        return VoiceStopDecision(
            should_stop=True,
            message="Encerrando.",
            voice_mode=voice_mode,
        )
    return VoiceStopDecision(should_stop=False)


def input_source_label(*, queued_user_input: str, voice_mode: bool) -> str:
    if queued_user_input:
        return "painel"
    if voice_mode:
        return "voz"
    return "texto"


def read_next_user_input(
    *,
    state: VoiceReadState,
    queued_user_input: str,
    waiting_for_direct_response: bool,
    read_user_input: Callable[..., str],
    wait_for_hotword: Callable[[bool, bool, bool], tuple[bool, bool, str]],
    set_voice_status: Callable[[str], None],
    terminal_print_user_command: Callable[[str, str], None],
    conversation_listener: Callable[..., str] | None = None,
    unreliable_conversation_filter: Callable[[str], bool] | None = None,
    transcription_artifact_filter: Callable[[str], bool] | None = None,
) -> VoiceReadResult:
    user_input = queued_user_input or ""
    inline_command = ""
    voice_paused = state.voice_paused
    direct_ready = state.direct_response_ready_announced
    conversation_ready = state.conversation_ready_announced
    dictation_ready = state.dictation_ready_announced

    modes = determine_listen_modes(
        voice_mode=state.voice_mode,
        hotword_mode=state.hotword_mode,
        voice_paused=voice_paused,
        waiting_for_direct_response=waiting_for_direct_response,
        conversation_mode=state.conversation_mode,
        dictation_mode=state.dictation_mode,
    )

    if queued_user_input:
        return VoiceReadResult(
            user_input=user_input,
            queued_user_input=queued_user_input,
            inline_command=inline_command,
            voice_paused=voice_paused,
            should_continue=True,
            modes=modes,
            direct_response_ready_announced=direct_ready,
            conversation_ready_announced=conversation_ready,
            dictation_ready_announced=dictation_ready,
        )

    repeat_listen_until = None
    if modes.direct_response:
        set_voice_status("RESPOSTA")
        repeat_prompt_mode = state.pending_command is None and state.pending_smart_open_choice is None
        user_input = read_user_input(
            state.voice_mode,
            announce_ready=not direct_ready,
            fallback_to_text=False,
            ready_message="Pode repetir..." if repeat_prompt_mode else "Pode responder...",
        )
        repeat_listen_until = 0.0
        direct_ready = True
    elif modes.conversation:
        set_voice_status("CONVERSA")
        user_input = read_user_input(
            state.voice_mode,
            announce_ready=not conversation_ready,
            fallback_to_text=False,
            ready_message="Pode falar comigo...",
            ignored_text_filter=unreliable_conversation_filter,
            listener=conversation_listener,
        )
        conversation_ready = True
    elif modes.dictation:
        set_voice_status("DITADO")
        user_input = read_user_input(
            state.voice_mode,
            announce_ready=not dictation_ready,
            fallback_to_text=False,
            ready_message="Pode ditar...",
            ignored_text_filter=transcription_artifact_filter,
            listener=conversation_listener,
        )
        dictation_ready = True
    elif state.voice_mode and state.hotword_mode:
        should_continue, voice_paused, inline_command = wait_for_hotword(
            state.voice_mode,
            state.hotword_mode,
            voice_paused,
        )
        if not should_continue:
            return VoiceReadResult(
                user_input="",
                queued_user_input=queued_user_input,
                inline_command=inline_command,
                voice_paused=voice_paused,
                should_continue=False,
                modes=modes,
                direct_response_ready_announced=direct_ready,
                conversation_ready_announced=conversation_ready,
                dictation_ready_announced=dictation_ready,
                repeat_listen_until=repeat_listen_until,
            )

    if should_use_inline_hotword_command(
        modes=modes,
        voice_mode=state.voice_mode,
        hotword_mode=state.hotword_mode,
        inline_command=inline_command,
    ):
        if inline_command.startswith(PANEL_INLINE_PREFIX):
            user_input = inline_command[len(PANEL_INLINE_PREFIX):]
            queued_user_input = user_input
            terminal_print_user_command("painel", user_input)
        else:
            terminal_print_user_command("voz", inline_command)
            user_input = inline_command
    elif should_read_default_input(
        queued_user_input=queued_user_input,
        modes=modes,
    ):
        user_input = read_user_input(
            state.voice_mode,
            announce_ready=not state.hotword_mode,
            fallback_to_text=not state.hotword_mode,
        )

    return VoiceReadResult(
        user_input=user_input,
        queued_user_input=queued_user_input,
        inline_command=inline_command,
        voice_paused=voice_paused,
        should_continue=True,
        modes=modes,
        direct_response_ready_announced=direct_ready,
        conversation_ready_announced=conversation_ready,
        dictation_ready_announced=dictation_ready,
        repeat_listen_until=repeat_listen_until,
    )


def run_voice_input_cycle(
    *,
    state: VoiceReadState,
    poll_ui_text_command: Callable[[], str],
    waiting_for_direct_response: Callable[[], bool],
    read_user_input: Callable[..., str],
    wait_for_hotword: Callable[[bool, bool, bool], tuple[bool, bool, str]],
    set_voice_status: Callable[[str], None],
    terminal_print_user_command: Callable[[str, str], None],
    conversation_listener: Callable[..., str] | None = None,
    unreliable_conversation_filter: Callable[[str], bool] | None = None,
    transcription_artifact_filter: Callable[[str], bool] | None = None,
) -> VoiceInputCycleResult:
    queued_user_input = poll_ui_text_command()
    if queued_user_input:
        terminal_print_user_command("painel", queued_user_input)

    voice_read = read_next_user_input(
        state=state,
        queued_user_input=queued_user_input,
        waiting_for_direct_response=waiting_for_direct_response(),
        read_user_input=read_user_input,
        wait_for_hotword=wait_for_hotword,
        set_voice_status=set_voice_status,
        terminal_print_user_command=terminal_print_user_command,
        conversation_listener=conversation_listener,
        unreliable_conversation_filter=unreliable_conversation_filter,
        transcription_artifact_filter=transcription_artifact_filter,
    )

    if not voice_read.should_continue:
        return VoiceInputCycleResult(
            user_input="",
            queued_user_input=queued_user_input,
            voice_paused=voice_read.voice_paused,
            should_break=True,
            direct_response_ready_announced=voice_read.direct_response_ready_announced,
            conversation_ready_announced=voice_read.conversation_ready_announced,
            dictation_ready_announced=voice_read.dictation_ready_announced,
            repeat_listen_until=voice_read.repeat_listen_until,
            hotword_ui_enabled=False,
            clear_status_line=True,
        )

    stop_decision = stop_decision_from_user_input(voice_read.user_input, state.voice_mode)
    if stop_decision.should_stop:
        return VoiceInputCycleResult(
            user_input=voice_read.user_input,
            queued_user_input=queued_user_input,
            voice_paused=voice_read.voice_paused,
            should_break=True,
            break_message=stop_decision.message,
            break_voice_mode=stop_decision.voice_mode,
            direct_response_ready_announced=voice_read.direct_response_ready_announced,
            conversation_ready_announced=voice_read.conversation_ready_announced,
            dictation_ready_announced=voice_read.dictation_ready_announced,
            repeat_listen_until=voice_read.repeat_listen_until,
            hotword_ui_enabled=False,
            clear_status_line=True,
        )

    return VoiceInputCycleResult(
        user_input=voice_read.user_input,
        queued_user_input=queued_user_input,
        voice_paused=voice_read.voice_paused,
        should_break=False,
        direct_response_ready_announced=voice_read.direct_response_ready_announced,
        conversation_ready_announced=voice_read.conversation_ready_announced,
        dictation_ready_announced=voice_read.dictation_ready_announced,
        repeat_listen_until=voice_read.repeat_listen_until,
    )
