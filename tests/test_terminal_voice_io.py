import unittest
from types import SimpleNamespace

from core.terminal_voice_io import TerminalVoiceIO


class TerminalVoiceIOTests(unittest.TestCase):
    def test_status_line_renders_when_hotword_ui_enabled(self):
        printed = []
        io = TerminalVoiceIO(print_fn=lambda *args, **kwargs: printed.append((args, kwargs)))
        io.hotword_ui_enabled = True

        io.set_voice_status("ATIVA", refresh_ui_runtime_state=lambda: None)

        self.assertEqual(io.voice_status, "ATIVA")
        self.assertEqual(io.rendered_status_line, "[ESCUTA: ATIVA]")
        self.assertIn("[ESCUTA: ATIVA]", printed[0][0][0])

    def test_user_command_print_is_deduplicated_briefly(self):
        printed = []
        now = iter([10.0, 10.5, 11.2])
        io = TerminalVoiceIO(
            print_fn=lambda *args, **kwargs: printed.append(args[0]),
            now_fn=lambda: next(now),
        )

        io.terminal_print_user_command("voz", "briefing")
        io.terminal_print_user_command("voz", "briefing")
        io.terminal_print_user_command("voz", "briefing")

        self.assertEqual(printed, ["Voce (voz): briefing", "Voce (voz): briefing"])

    def test_user_command_dedup_suppresses_same_text_across_sources(self):
        printed = []
        now = iter([10.0, 10.5])
        io = TerminalVoiceIO(
            print_fn=lambda *args, **kwargs: printed.append(args[0]),
            now_fn=lambda: next(now),
        )

        io.terminal_print_user_command("painel", "qual o assunto?")
        io.terminal_print_user_command("voz", "qual o assunto?")

        self.assertEqual(printed, ["Voce (painel): qual o assunto?"])

    def test_read_text_input_updates_history(self):
        history = []
        runtime = []
        io = TerminalVoiceIO(input_fn=lambda prompt: " briefing ")

        result = io.read_user_input(
            False,
            append_ui_history=lambda *args, **kwargs: history.append((args, kwargs)),
            refresh_ui_runtime_state=runtime.append,
            listen_once=lambda: None,
        )

        self.assertEqual(result, "briefing")
        self.assertEqual(history[0][0], ("user", "briefing"))
        self.assertEqual(runtime, [{"last_heard": "briefing"}])

    def test_read_voice_input_updates_history(self):
        history = []
        runtime = []
        printed = []
        io = TerminalVoiceIO(print_fn=lambda *args, **kwargs: printed.append(args[0]))

        result = io.read_user_input(
            True,
            append_ui_history=lambda *args, **kwargs: history.append((args, kwargs)),
            refresh_ui_runtime_state=runtime.append,
            listen_once=lambda: SimpleNamespace(ok=True, text=" abrir chrome ", error=""),
        )

        self.assertEqual(result, "abrir chrome")
        self.assertEqual(history[0][0], ("user", "abrir chrome"))
        self.assertEqual(runtime, [{"last_heard": "abrir chrome"}])

    def test_read_voice_assistant_messages_are_polished(self):
        printed = []
        io = TerminalVoiceIO(
            print_fn=lambda *args, **kwargs: printed.append(args[0]),
            input_fn=lambda _prompt: "",
        )

        io.read_user_input(
            True,
            append_ui_history=lambda *args, **kwargs: None,
            refresh_ui_runtime_state=lambda _patch: None,
            listen_once=lambda: SimpleNamespace(ok=False, text="", error="Nao detectei fala no microfone"),
            ready_message="Pode falar",
        )

        self.assertEqual(printed[0], "IA: Pode falar.")
        self.assertEqual(printed[1], "IA: Não detectei fala no microfone.")

    def test_wait_for_hotword_returns_queued_panel_command(self):
        io = TerminalVoiceIO(print_fn=lambda *args, **kwargs: None)
        refreshes = []

        result = io.wait_for_hotword(
            voice_mode=True,
            hotword_mode=True,
            voice_paused=False,
            maybe_announce_due_reminders=lambda voice_mode: None,
            hotword_listening_enabled=True,
            hotkey_name="F8",
            poll_ui_text_command=lambda: "briefing",
            consume_toggle_listening_hotkey_press=lambda: False,
            consume_hotkey_press=lambda: False,
            play_activation_sound=lambda: None,
            listen_for_hotword=lambda: SimpleNamespace(ok=False, command_text="", error=""),
            output_response=lambda *args, **kwargs: None,
            refresh_ui_runtime_state=lambda: refreshes.append(True),
        )

        self.assertEqual(result, (True, False, "\0panel:briefing"))
        self.assertEqual(io.voice_status, "COMANDO")
        self.assertTrue(refreshes)

    def test_wait_for_hotword_uses_configurable_idle_sleep(self):
        sleeps = []
        polls = iter(["", "briefing"])
        io = TerminalVoiceIO(
            print_fn=lambda *args, **kwargs: None,
            sleep_fn=sleeps.append,
        )

        result = io.wait_for_hotword(
            voice_mode=True,
            hotword_mode=True,
            voice_paused=True,
            maybe_announce_due_reminders=lambda voice_mode: None,
            hotword_listening_enabled=True,
            hotkey_name="F8",
            poll_ui_text_command=lambda: next(polls),
            consume_toggle_listening_hotkey_press=lambda: False,
            consume_hotkey_press=lambda: False,
            play_activation_sound=lambda: None,
            listen_for_hotword=lambda: SimpleNamespace(ok=False, command_text="", error=""),
            output_response=lambda *args, **kwargs: None,
            refresh_ui_runtime_state=lambda: None,
            idle_sleep_seconds=lambda: 0.25,
        )

        self.assertEqual(result, (True, True, "\0panel:briefing"))
        self.assertEqual(sleeps, [0.25])


if __name__ == "__main__":
    unittest.main()
