import unittest

from core.voice_loop import (
    VoiceReadState,
    determine_listen_modes,
    input_source_label,
    read_next_user_input,
    run_voice_input_cycle,
    should_read_default_input,
    should_use_inline_hotword_command,
    stop_decision_from_user_input,
)


class VoiceLoopTests(unittest.TestCase):
    def test_direct_response_has_priority(self):
        modes = determine_listen_modes(
            voice_mode=True,
            hotword_mode=True,
            voice_paused=False,
            waiting_for_direct_response=True,
            conversation_mode=True,
            dictation_mode=True,
        )

        self.assertTrue(modes.direct_response)
        self.assertFalse(modes.conversation)
        self.assertFalse(modes.dictation)
        self.assertTrue(modes.any_modal)

    def test_conversation_mode_requires_hotword_voice_and_not_paused(self):
        modes = determine_listen_modes(
            voice_mode=True,
            hotword_mode=True,
            voice_paused=False,
            waiting_for_direct_response=False,
            conversation_mode=True,
            dictation_mode=False,
        )

        self.assertFalse(modes.direct_response)
        self.assertTrue(modes.conversation)
        self.assertFalse(modes.dictation)

    def test_dictation_is_blocked_by_conversation(self):
        modes = determine_listen_modes(
            voice_mode=True,
            hotword_mode=True,
            voice_paused=False,
            waiting_for_direct_response=False,
            conversation_mode=True,
            dictation_mode=True,
        )

        self.assertTrue(modes.conversation)
        self.assertFalse(modes.dictation)

    def test_all_modes_off_when_voice_is_paused(self):
        modes = determine_listen_modes(
            voice_mode=True,
            hotword_mode=True,
            voice_paused=True,
            waiting_for_direct_response=True,
            conversation_mode=True,
            dictation_mode=True,
        )

        self.assertFalse(modes.any_modal)

    def test_inline_hotword_command_runs_only_without_modal_mode(self):
        modes = determine_listen_modes(
            voice_mode=True,
            hotword_mode=True,
            voice_paused=False,
            waiting_for_direct_response=False,
            conversation_mode=False,
            dictation_mode=False,
        )

        self.assertTrue(
            should_use_inline_hotword_command(
                modes=modes,
                voice_mode=True,
                hotword_mode=True,
                inline_command="abrir chrome",
            )
        )

    def test_default_input_runs_when_no_queue_and_no_modal_mode(self):
        modes = determine_listen_modes(
            voice_mode=False,
            hotword_mode=False,
            voice_paused=False,
            waiting_for_direct_response=False,
            conversation_mode=False,
            dictation_mode=False,
        )

        self.assertTrue(should_read_default_input(queued_user_input="", modes=modes))
        self.assertFalse(should_read_default_input(queued_user_input="briefing", modes=modes))

    def test_read_next_user_input_uses_queued_panel_text(self):
        result = read_next_user_input(
            state=VoiceReadState(
                voice_mode=True,
                hotword_mode=True,
                voice_paused=False,
                direct_response_ready_announced=False,
                conversation_ready_announced=False,
                dictation_ready_announced=False,
                conversation_mode=False,
                dictation_mode=False,
            ),
            queued_user_input="briefing",
            waiting_for_direct_response=False,
            read_user_input=lambda *args, **kwargs: "nao deveria ler",
            wait_for_hotword=lambda *_args: (True, False, ""),
            set_voice_status=lambda _status: None,
            terminal_print_user_command=lambda *_args: None,
        )

        self.assertEqual(result.user_input, "briefing")
        self.assertTrue(result.should_continue)

    def test_read_next_user_input_handles_direct_response(self):
        statuses = []

        result = read_next_user_input(
            state=VoiceReadState(
                voice_mode=True,
                hotword_mode=True,
                voice_paused=False,
                direct_response_ready_announced=False,
                conversation_ready_announced=False,
                dictation_ready_announced=False,
                conversation_mode=False,
                dictation_mode=False,
            ),
            queued_user_input="",
            waiting_for_direct_response=True,
            read_user_input=lambda *args, **kwargs: kwargs["ready_message"],
            wait_for_hotword=lambda *_args: (True, False, ""),
            set_voice_status=statuses.append,
            terminal_print_user_command=lambda *_args: None,
        )

        self.assertEqual(statuses, ["RESPOSTA"])
        self.assertEqual(result.user_input, "Pode repetir...")
        self.assertTrue(result.direct_response_ready_announced)
        self.assertEqual(result.repeat_listen_until, 0.0)

    def test_read_next_user_input_uses_inline_hotword_command(self):
        printed = []

        result = read_next_user_input(
            state=VoiceReadState(
                voice_mode=True,
                hotword_mode=True,
                voice_paused=False,
                direct_response_ready_announced=False,
                conversation_ready_announced=False,
                dictation_ready_announced=False,
                conversation_mode=False,
                dictation_mode=False,
            ),
            queued_user_input="",
            waiting_for_direct_response=False,
            read_user_input=lambda *args, **kwargs: "nao deveria ler",
            wait_for_hotword=lambda *_args: (True, False, "abrir chrome"),
            set_voice_status=lambda _status: None,
            terminal_print_user_command=lambda source, text: printed.append((source, text)),
        )

        self.assertEqual(result.user_input, "abrir chrome")
        self.assertEqual(printed, [("voz", "abrir chrome")])

    def test_read_next_user_input_keeps_panel_command_from_hotword_wait_source(self):
        printed = []

        result = read_next_user_input(
            state=VoiceReadState(
                voice_mode=True,
                hotword_mode=True,
                voice_paused=False,
                direct_response_ready_announced=False,
                conversation_ready_announced=False,
                dictation_ready_announced=False,
                conversation_mode=False,
                dictation_mode=False,
            ),
            queued_user_input="",
            waiting_for_direct_response=False,
            read_user_input=lambda *args, **kwargs: "nao deveria ler",
            wait_for_hotword=lambda *_args: (True, False, "\0panel:briefing"),
            set_voice_status=lambda _status: None,
            terminal_print_user_command=lambda source, text: printed.append((source, text)),
        )

        self.assertEqual(result.user_input, "briefing")
        self.assertEqual(result.queued_user_input, "briefing")
        self.assertEqual(printed, [("painel", "briefing")])

    def test_read_next_user_input_can_stop_from_hotword(self):
        result = read_next_user_input(
            state=VoiceReadState(
                voice_mode=True,
                hotword_mode=True,
                voice_paused=False,
                direct_response_ready_announced=False,
                conversation_ready_announced=False,
                dictation_ready_announced=False,
                conversation_mode=False,
                dictation_mode=False,
            ),
            queued_user_input="",
            waiting_for_direct_response=False,
            read_user_input=lambda *args, **kwargs: "nao deveria ler",
            wait_for_hotword=lambda *_args: (False, True, ""),
            set_voice_status=lambda _status: None,
            terminal_print_user_command=lambda *_args: None,
        )

        self.assertFalse(result.should_continue)
        self.assertTrue(result.voice_paused)

    def test_stop_decision_from_user_input_accepts_exit_commands(self):
        decision = stop_decision_from_user_input(" sair ", voice_mode=True)

        self.assertTrue(decision.should_stop)
        self.assertEqual(decision.message, "Encerrando.")
        self.assertTrue(decision.voice_mode)

    def test_stop_decision_from_user_input_ignores_regular_text(self):
        decision = stop_decision_from_user_input("briefing", voice_mode=True)

        self.assertFalse(decision.should_stop)
        self.assertEqual(decision.message, "")

    def test_input_source_label_prioritizes_panel_then_voice_then_text(self):
        self.assertEqual(input_source_label(queued_user_input="briefing", voice_mode=True), "painel")
        self.assertEqual(input_source_label(queued_user_input="", voice_mode=True), "voz")
        self.assertEqual(input_source_label(queued_user_input="", voice_mode=False), "texto")

    def test_run_voice_input_cycle_reads_panel_command(self):
        printed = []

        result = run_voice_input_cycle(
            state=VoiceReadState(
                voice_mode=True,
                hotword_mode=True,
                voice_paused=False,
                direct_response_ready_announced=False,
                conversation_ready_announced=False,
                dictation_ready_announced=False,
                conversation_mode=False,
                dictation_mode=False,
            ),
            poll_ui_text_command=lambda: "briefing",
            waiting_for_direct_response=lambda: False,
            read_user_input=lambda *args, **kwargs: "nao deveria ler",
            wait_for_hotword=lambda *_args: (True, False, ""),
            set_voice_status=lambda _status: None,
            terminal_print_user_command=lambda source, text: printed.append((source, text)),
        )

        self.assertEqual(result.user_input, "briefing")
        self.assertEqual(result.queued_user_input, "briefing")
        self.assertFalse(result.should_break)
        self.assertEqual(printed, [("painel", "briefing")])

    def test_run_voice_input_cycle_breaks_on_exit_command(self):
        result = run_voice_input_cycle(
            state=VoiceReadState(
                voice_mode=False,
                hotword_mode=False,
                voice_paused=False,
                direct_response_ready_announced=False,
                conversation_ready_announced=False,
                dictation_ready_announced=False,
                conversation_mode=False,
                dictation_mode=False,
            ),
            poll_ui_text_command=lambda: "sair",
            waiting_for_direct_response=lambda: False,
            read_user_input=lambda *args, **kwargs: "nao deveria ler",
            wait_for_hotword=lambda *_args: (True, False, ""),
            set_voice_status=lambda _status: None,
            terminal_print_user_command=lambda *_args: None,
        )

        self.assertTrue(result.should_break)
        self.assertEqual(result.break_message, "Encerrando.")
        self.assertFalse(result.break_voice_mode)
        self.assertFalse(result.hotword_ui_enabled)
        self.assertTrue(result.clear_status_line)


if __name__ == "__main__":
    unittest.main()
