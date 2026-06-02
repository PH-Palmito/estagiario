from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class TerminalVoiceIO:
    ui_history_max_items: int = 40
    print_fn: Callable[..., None] = print
    input_fn: Callable[[str], str] = input
    now_fn: Callable[[], float] = time.time
    sleep_fn: Callable[[float], None] = time.sleep
    voice_status: str | None = None
    hotword_ui_enabled: bool = False
    rendered_status_line: str = ""
    last_user_command_printed: str = ""
    last_user_command_printed_at: float = 0.0

    def set_voice_status(self, status: str, *, refresh_ui_runtime_state: Callable[[], None]) -> None:
        if self.voice_status == status:
            return

        self.voice_status = status
        self.render_status_line()
        refresh_ui_runtime_state()

    def clear_status_line(self) -> None:
        if not self.rendered_status_line:
            return

        self.print_fn("\r" + (" " * len(self.rendered_status_line)) + "\r", end="", flush=True)
        self.rendered_status_line = ""

    def terminal_print(self, message: str) -> None:
        self.clear_status_line()
        self.print_fn(message)
        self.render_status_line()

    def terminal_print_user_command(self, source: str, text: str) -> None:
        content = str(text or "").strip()
        if not content:
            return

        label = str(source or "comando").strip().lower()
        fingerprint = content
        now = self.now_fn()
        if self.last_user_command_printed == fingerprint and now - self.last_user_command_printed_at < 1.0:
            return

        self.terminal_print(f"Voce ({label}): {content}")
        self.last_user_command_printed = fingerprint
        self.last_user_command_printed_at = now

    def terminal_input(self, prompt: str) -> str:
        self.clear_status_line()
        try:
            return self.input_fn(prompt).strip()
        finally:
            self.render_status_line()

    def render_status_line(self) -> None:
        if not self.hotword_ui_enabled or not self.voice_status:
            self.rendered_status_line = ""
            return

        self.rendered_status_line = f"[ESCUTA: {self.voice_status}]"
        self.print_fn(f"\r{self.rendered_status_line:<24}", end="", flush=True)

    def read_user_input(
        self,
        voice_mode: bool,
        *,
        append_ui_history: Callable[..., None],
        refresh_ui_runtime_state: Callable[[dict | None], None],
        listen_once: Callable[[], object],
        announce_ready: bool = True,
        fallback_to_text: bool = True,
        ready_message: str = "Pode falar...",
        ignored_text_filter=None,
        listener=None,
    ) -> str:
        if not voice_mode:
            typed = self.terminal_input("Voce: ")
            if typed:
                append_ui_history("user", typed, max_items=self.ui_history_max_items)
                refresh_ui_runtime_state({"last_heard": typed})
            return typed

        if announce_ready:
            self.terminal_print(f"IA: {ready_message}")
        listen = listener or listen_once
        heard = listen()

        if heard.ok:
            text = heard.text.strip()
            if ignored_text_filter and ignored_text_filter(text):
                return ""
            self.terminal_print_user_command("voz", text)
            append_ui_history("user", text, max_items=self.ui_history_max_items)
            refresh_ui_runtime_state({"last_heard": text})
            return text

        if not fallback_to_text and heard.error in {
            "Nao detectei fala no microfone.",
            "Nenhuma fala reconhecida.",
        }:
            return ""

        self.terminal_print(f"IA: {heard.error}")

        if not fallback_to_text:
            return ""

        typed = self.terminal_input("Voce (texto): ")
        if typed:
            append_ui_history("user", typed, max_items=self.ui_history_max_items)
            refresh_ui_runtime_state({"last_heard": typed})
        return typed

    def wait_for_hotword(
        self,
        *,
        voice_mode: bool,
        hotword_mode: bool,
        voice_paused: bool,
        maybe_announce_due_reminders: Callable[[bool], None],
        hotword_listening_enabled: bool,
        hotkey_name: str,
        poll_ui_text_command: Callable[[], str],
        consume_toggle_listening_hotkey_press: Callable[[], bool],
        consume_hotkey_press: Callable[[], bool],
        play_activation_sound: Callable[[], None],
        listen_for_hotword: Callable[[], object],
        output_response: Callable[..., None],
        refresh_ui_runtime_state: Callable[[], None],
        idle_sleep_seconds: Callable[[], float] | None = None,
    ) -> tuple[bool, bool, str]:
        if not hotword_mode:
            return True, voice_paused, ""

        def idle_sleep() -> None:
            delay = idle_sleep_seconds() if idle_sleep_seconds is not None else 0.08
            self.sleep_fn(max(0.02, float(delay)))

        while True:
            maybe_announce_due_reminders(voice_mode)

            if not voice_paused:
                self.set_voice_status(
                    "ATIVA" if hotword_listening_enabled else f"BOTAO {hotkey_name}",
                    refresh_ui_runtime_state=refresh_ui_runtime_state,
                )

            queued_command = poll_ui_text_command()
            if queued_command:
                self.set_voice_status("COMANDO", refresh_ui_runtime_state=refresh_ui_runtime_state)
                return True, voice_paused, "\0panel:" + queued_command

            if consume_toggle_listening_hotkey_press():
                voice_paused = not voice_paused
                if voice_paused:
                    self.set_voice_status("PAUSADA", refresh_ui_runtime_state=refresh_ui_runtime_state)
                    output_response("Escuta pausada.", voice_mode=False)
                else:
                    self.set_voice_status("ATIVA", refresh_ui_runtime_state=refresh_ui_runtime_state)
                    output_response("Escuta retomada.", voice_mode=False)
                self.sleep_fn(0.15)
                continue

            if voice_paused:
                idle_sleep()
                continue

            if consume_hotkey_press():
                play_activation_sound()
                self.set_voice_status("COMANDO", refresh_ui_runtime_state=refresh_ui_runtime_state)
                output_response("Pode falar.", voice_mode=False)
                return True, voice_paused, ""

            if not hotword_listening_enabled:
                idle_sleep()
                continue

            heard = listen_for_hotword()

            if heard.ok:
                play_activation_sound()
                if heard.command_text:
                    self.set_voice_status("ATIVA", refresh_ui_runtime_state=refresh_ui_runtime_state)
                    return True, voice_paused, heard.command_text

                self.set_voice_status("COMANDO", refresh_ui_runtime_state=refresh_ui_runtime_state)
                output_response("Pode falar.", voice_mode=False)
                return True, voice_paused, ""

            if heard.error.startswith("Falha ao acessar o microfone"):
                output_response(heard.error, voice_mode=False)
                return False, voice_paused, ""
