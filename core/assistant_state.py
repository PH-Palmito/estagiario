from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class AssistantState:
    pending_command: object | None = None
    pending_command_learning_text: str = ""
    pending_smart_open_choice: object | None = None
    pending_smart_open_invalid_attempts: int = 0
    conversation_mode: bool = False
    conversation_ready_announced: bool = False
    dictation_mode: bool = False
    dictation_ready_announced: bool = False
    direct_response_ready_announced: bool = False
    last_voice_text: str = ""
    repeat_listen_until: float = 0.0
    silent_ui_command_active: bool = False
    creating_macro: bool = False
    macro_name: str | None = None
    macro_steps: list[dict] = field(default_factory=list)

    def is_waiting_for_direct_response(self, now: float | None = None) -> bool:
        active_now = time.time() if now is None else now
        return (
            self.pending_command is not None
            or self.pending_smart_open_choice is not None
            or self.repeat_listen_until > active_now
        )

    def apply_direct_response_state(self, state: object) -> None:
        self.pending_command = getattr(state, "pending_command")
        self.pending_command_learning_text = getattr(state, "pending_command_learning_text")
        self.pending_smart_open_choice = getattr(state, "pending_smart_open_choice")
        self.pending_smart_open_invalid_attempts = getattr(state, "pending_smart_open_invalid_attempts")
        self.direct_response_ready_announced = getattr(state, "direct_response_ready_announced")

    def to_direct_response_state(self):
        from core.direct_response_flow import DirectResponseState

        return DirectResponseState(
            pending_command=self.pending_command,
            pending_command_learning_text=self.pending_command_learning_text,
            pending_smart_open_choice=self.pending_smart_open_choice,
            pending_smart_open_invalid_attempts=self.pending_smart_open_invalid_attempts,
            direct_response_ready_announced=self.direct_response_ready_announced,
        )

    def apply_interactive_modes_state(self, state: object) -> None:
        self.dictation_mode = getattr(state, "dictation_mode")
        self.dictation_ready_announced = getattr(state, "dictation_ready_announced")
        self.conversation_mode = getattr(state, "conversation_mode")
        self.conversation_ready_announced = getattr(state, "conversation_ready_announced")

    def to_interactive_modes_state(self):
        from core.interactive_modes import InteractiveModesState

        return InteractiveModesState(
            dictation_mode=self.dictation_mode,
            dictation_ready_announced=self.dictation_ready_announced,
            conversation_mode=self.conversation_mode,
            conversation_ready_announced=self.conversation_ready_announced,
        )

    def apply_macro_recording_state(self, state: object) -> None:
        self.creating_macro = getattr(state, "creating_macro")
        self.macro_name = getattr(state, "macro_name")
        self.macro_steps = getattr(state, "macro_steps")

    def to_macro_recording_state(self):
        from core.macro_recording import MacroRecordingState

        return MacroRecordingState(
            creating_macro=self.creating_macro,
            macro_name=self.macro_name,
            macro_steps=self.macro_steps,
        )

    def apply_post_route_state(self, state: object) -> None:
        self.pending_command = getattr(state, "pending_command")
        self.pending_command_learning_text = getattr(state, "pending_command_learning_text")
        self.pending_smart_open_choice = getattr(state, "pending_smart_open_choice")
        self.pending_smart_open_invalid_attempts = getattr(state, "pending_smart_open_invalid_attempts")
        self.direct_response_ready_announced = getattr(state, "direct_response_ready_announced")
        self.conversation_mode = getattr(state, "conversation_mode")
        self.conversation_ready_announced = getattr(state, "conversation_ready_announced")

    def to_post_route_state(self):
        from core.post_route_flow import PostRouteState

        return PostRouteState(
            pending_command=self.pending_command,
            pending_command_learning_text=self.pending_command_learning_text,
            pending_smart_open_choice=self.pending_smart_open_choice,
            pending_smart_open_invalid_attempts=self.pending_smart_open_invalid_attempts,
            direct_response_ready_announced=self.direct_response_ready_announced,
            conversation_mode=self.conversation_mode,
            conversation_ready_announced=self.conversation_ready_announced,
        )

    def to_voice_read_state(self, *, voice_mode: bool, hotword_mode: bool, voice_paused: bool):
        from core.voice_loop import VoiceReadState

        return VoiceReadState(
            voice_mode=voice_mode,
            hotword_mode=hotword_mode,
            voice_paused=voice_paused,
            direct_response_ready_announced=self.direct_response_ready_announced,
            conversation_ready_announced=self.conversation_ready_announced,
            dictation_ready_announced=self.dictation_ready_announced,
            conversation_mode=self.conversation_mode,
            dictation_mode=self.dictation_mode,
            pending_command=self.pending_command,
            pending_smart_open_choice=self.pending_smart_open_choice,
        )

    def apply_voice_cycle_result(self, result: object) -> None:
        self.direct_response_ready_announced = getattr(result, "direct_response_ready_announced")
        self.conversation_ready_announced = getattr(result, "conversation_ready_announced")
        self.dictation_ready_announced = getattr(result, "dictation_ready_announced")
        repeat_listen_until = getattr(result, "repeat_listen_until")
        if repeat_listen_until is not None:
            self.repeat_listen_until = repeat_listen_until
