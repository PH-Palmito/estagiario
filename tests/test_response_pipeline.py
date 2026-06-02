import unittest
from unittest.mock import patch

from core.command_schema import Command
from core.response_pipeline import ResponsePipeline


class FakeRuntimeState:
    def __init__(self):
        self.updated = []

    def update(self, command, result):
        self.updated.append((command, result))


class ResponsePipelineTests(unittest.TestCase):
    def _pipeline(self, **overrides):
        calls = {
            "terminal": [],
            "history": [],
            "runtime": [],
            "speak": [],
            "events": [],
            "improvements": [],
        }
        state = FakeRuntimeState()
        params = {
            "preferences": {},
            "style_variants": {},
            "progress_variants": {"daily_briefing": ("Montando briefing...",)},
            "next_phrase": lambda _key, options, *_args: options[0],
            "terminal_print": calls["terminal"].append,
            "append_ui_history": lambda *args, **kwargs: calls["history"].append((args, kwargs)),
            "refresh_ui_runtime_state": calls["runtime"].append,
            "refresh_improvement_brain": lambda: calls["improvements"].append(True),
            "current_ui_mode_label": lambda: "comando",
            "speak": lambda *args, **kwargs: calls["speak"].append((args, kwargs)),
            "execute": lambda command: f"result:{command.action}",
            "runtime_state": state,
            "log_event": lambda event, **payload: calls["events"].append((event, payload)),
            "history_max_items": 7,
            "now_fn": lambda: 100.0,
        }
        params.update(overrides)
        return ResponsePipeline(**params), calls, state

    def test_show_action_progress_updates_terminal_history_and_tts(self):
        pipeline, calls, _state = self._pipeline()

        pipeline.show_action_progress(Command(action="daily_briefing"), voice_mode=True)

        self.assertEqual(calls["terminal"], ["IA: Montando briefing..."])
        self.assertEqual(calls["history"][0][0], ("assistant", "Montando briefing..."))
        self.assertEqual(calls["runtime"], [{"status": "PROCESSANDO", "last_response": "Montando briefing..."}])
        self.assertEqual(calls["speak"][0][0], ("Montando briefing...",))
        self.assertEqual(calls["events"][-1][0], "latency_stage")
        self.assertEqual(calls["events"][-1][1]["stage"], "tts")

    def test_execute_command_runs_progress_and_updates_state(self):
        pipeline, calls, state = self._pipeline()
        command = Command(action="daily_briefing")

        with patch("core.background_tasks.submit_background_task", return_value="bg-7"):
            result = pipeline.execute_command(command, voice_mode=True)

        self.assertEqual(result, "Deixei daily_briefing rodando em segundo plano. Tarefa: bg-7.")
        self.assertEqual(state.updated, [(command, result)])
        self.assertIn("command_auto_background", [event for event, _payload in calls["events"]])

    def test_output_response_logs_history_runtime_and_speaks(self):
        pipeline, calls, _state = self._pipeline()

        result = pipeline.output_response(
            "Tudo pronto.",
            True,
            direct_response_ready_announced=True,
            wait_for_tts=True,
        )

        self.assertEqual(result.styled_message, "Tudo pronto.")
        self.assertEqual(calls["terminal"], ["IA: Tudo pronto."])
        self.assertEqual(calls["history"][0][0], ("assistant", "Tudo pronto."))
        self.assertEqual(calls["runtime"], [{"last_response": "Tudo pronto."}])
        self.assertEqual(calls["improvements"], [True])
        self.assertEqual(calls["speak"][0], (("Tudo pronto.",), {"interrupt_current": False, "wait_for_playback": True}))
        self.assertEqual([event for event, _payload in calls["events"]], ["assistant_output", "latency_stage", "latency_stage"])
        self.assertEqual(calls["events"][-2][1]["stage"], "tts")
        self.assertEqual(calls["events"][-1][1]["stage"], "output")

    def test_output_response_sets_repeat_window_for_unclear_voice_response(self):
        pipeline, _calls, _state = self._pipeline()

        result = pipeline.output_response(
            "Pode repetir?",
            True,
            direct_response_ready_announced=True,
        )

        self.assertEqual(result.repeat_listen_until, 108.0)
        self.assertFalse(result.direct_response_ready_announced)

    def test_output_response_polishes_common_portuguese(self):
        pipeline, calls, _state = self._pipeline()

        result = pipeline.output_response(
            "Nao encontrei microfones disponiveis. O que voce quer fazer?",
            False,
            direct_response_ready_announced=True,
        )

        self.assertEqual(result.styled_message, "Não encontrei microfones disponíveis. O que você quer fazer?")
        self.assertEqual(calls["terminal"], [f"IA: {result.styled_message}"])

    def test_action_progress_polishes_common_portuguese(self):
        pipeline, calls, _state = self._pipeline(
            progress_variants={"daily_briefing": ("Nao consegui iniciar a acao.",)}
        )

        pipeline.show_action_progress(Command(action="daily_briefing"), voice_mode=True)

        self.assertEqual(calls["terminal"], ["IA: Não consegui iniciar a ação."])
        self.assertEqual(calls["speak"][0][0], ("Não consegui iniciar a ação.",))

    def test_silent_ui_command_skips_tts(self):
        pipeline, calls, _state = self._pipeline()

        pipeline.output_response(
            "Tudo pronto.",
            True,
            direct_response_ready_announced=True,
            silent_ui_command_active=True,
        )

        self.assertEqual(calls["speak"], [])

    def test_output_response_blocks_corrupted_study_pdf_text(self):
        pipeline, calls, _state = self._pipeline()
        corrupted = (
            "Analise de estudo dos arquivos: 1. questoes.pdf: - "
            "T m s t m s m Q u i t q l i l m l m S o n t w i r m "
            "Qumstao ciqxi quivtos cisos lm tmstm couxtmx trivsn qvvÃ¡t."
        )

        result = pipeline.output_response(
            corrupted,
            False,
            direct_response_ready_announced=True,
        )

        self.assertIn("falhou na verificação de confiança", result.styled_message)
        self.assertNotIn("T m s t m s", result.styled_message)
        self.assertEqual(calls["terminal"], [f"IA: {result.styled_message}"])

    def test_output_response_blocks_corrupted_study_pdf_text_with_nuls(self):
        pipeline, _calls, _state = self._pipeline()
        body = (
            "Analise de estudo dos arquivos: 1. questoes.pdf: - "
            "T m s t m s m Q u i t q l i l m l m S o n t w i r m "
            "Qumstao ciqxi quivtos cisos lm tmstm couxtmx trivsn qvvÃ¡t."
        )
        corrupted = "".join("\x00" + char for char in body)

        result = pipeline.output_response(
            corrupted,
            False,
            direct_response_ready_announced=True,
        )

        self.assertIn("falhou na verificação de confiança", result.styled_message)
        self.assertNotIn("Qumstao", result.styled_message)


if __name__ == "__main__":
    unittest.main()
