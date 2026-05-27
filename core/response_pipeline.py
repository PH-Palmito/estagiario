from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from core.command_feedback import action_progress_message
from core.command_service import execute_processed_command
from core.latency_metrics import log_latency_stage
from core.response_style import style_response
from memory.session import add_turn


@dataclass(frozen=True)
class OutputResponseResult:
    styled_message: str
    repeat_listen_until: float | None
    direct_response_ready_announced: bool


class ResponsePipeline:
    def __init__(
        self,
        *,
        preferences: dict,
        style_variants: dict,
        progress_variants: dict,
        next_phrase: Callable[..., str],
        terminal_print: Callable[[str], None],
        append_ui_history: Callable[..., None],
        refresh_ui_runtime_state: Callable[[dict | None], None],
        refresh_improvement_brain: Callable[[], None],
        current_ui_mode_label: Callable[[], str],
        speak: Callable[..., None],
        execute: Callable[[object], str],
        runtime_state,
        log_event: Callable[..., None],
        history_max_items: int = 40,
        now_fn: Callable[[], float] = time.time,
    ):
        self.preferences = preferences
        self.style_variants = style_variants
        self.progress_variants = progress_variants
        self.next_phrase = next_phrase
        self.terminal_print = terminal_print
        self.append_ui_history = append_ui_history
        self.refresh_ui_runtime_state = refresh_ui_runtime_state
        self.refresh_improvement_brain = refresh_improvement_brain
        self.current_ui_mode_label = current_ui_mode_label
        self.speak = speak
        self.execute = execute
        self.runtime_state = runtime_state
        self.log_event = log_event
        self.history_max_items = history_max_items
        self.now_fn = now_fn
        self.style_state: dict[str, object] = {}

    def show_action_progress(
        self,
        command,
        *,
        voice_mode: bool = False,
        silent_ui_command_active: bool = False,
    ) -> None:
        message = action_progress_message(
            command,
            next_phrase=self.next_phrase,
            variants=self.progress_variants,
        )
        if not message:
            return
        self.terminal_print(f"IA: {message}")
        self.append_ui_history("assistant", message, max_items=self.history_max_items)
        self.refresh_ui_runtime_state({"status": "PROCESSANDO", "last_response": message})
        if voice_mode and not silent_ui_command_active:
            tts_started_at = time.perf_counter()
            self.speak(message)
            log_latency_stage(
                self.log_event,
                "tts",
                tts_started_at,
                source="action_progress",
                voice_mode=voice_mode,
            )

    def execute_command(
        self,
        command,
        *,
        voice_mode: bool = False,
        silent_ui_command_active: bool = False,
    ) -> str:
        return execute_processed_command(
            command,
            self.runtime_state,
            self.execute,
            self.log_event,
            progress_callback=lambda processed: self.show_action_progress(
                processed,
                voice_mode=voice_mode,
                silent_ui_command_active=silent_ui_command_active,
            ),
            voice_mode=voice_mode,
        )

    def style_response(self, message: str) -> str:
        return style_response(
            message,
            preferences=self.preferences,
            variants=self.style_variants,
            next_phrase=self.next_phrase,
            state=self.style_state,
        )

    def output_response(
        self,
        message: str,
        voice_mode: bool,
        *,
        direct_response_ready_announced: bool,
        silent_ui_command_active: bool = False,
        interrupt_current_tts: bool = False,
        wait_for_tts: bool | None = None,
    ) -> OutputResponseResult:
        output_started_at = time.perf_counter()
        styled_message = self.style_response(message)
        self.log_event(
            "assistant_output",
            message=styled_message,
            voice_mode=voice_mode,
            mode=self.current_ui_mode_label(),
        )
        self.terminal_print(f"IA: {styled_message}")
        self.append_ui_history("assistant", styled_message, max_items=self.history_max_items)
        add_turn("assistant", styled_message, source="response")
        self.refresh_ui_runtime_state({"last_response": styled_message})
        self.refresh_improvement_brain()

        repeat_listen_until = None
        if voice_mode and any(
            phrase in styled_message
            for phrase in (
                "Não captei com precisão",
                "Não identifiquei o comando",
                "Não captei com precisão",
                "Não identifiquei o comando",
                "Pode repetir",
            )
        ):
            repeat_listen_until = self.now_fn() + 8.0
            direct_response_ready_announced = False

        quiet_messages = {
            "Nao entendi.",
            "Pode repetir?",
            "Nao identifiquei o comando.",
        }

        if voice_mode and not silent_ui_command_active and styled_message not in quiet_messages:
            tts_started_at = time.perf_counter()
            self.speak(
                styled_message,
                interrupt_current=interrupt_current_tts,
                wait_for_playback=wait_for_tts,
            )
            log_latency_stage(
                self.log_event,
                "tts",
                tts_started_at,
                source="assistant_output",
                voice_mode=voice_mode,
                wait_for_playback=wait_for_tts,
            )

        log_latency_stage(
            self.log_event,
            "output",
            output_started_at,
            voice_mode=voice_mode,
            tts_requested=bool(
                voice_mode and not silent_ui_command_active and styled_message not in quiet_messages
            ),
        )

        return OutputResponseResult(
            styled_message=styled_message,
            repeat_listen_until=repeat_listen_until,
            direct_response_ready_announced=direct_response_ready_announced,
        )
