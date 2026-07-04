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

    def test_output_response_preserves_demonstrative_esta(self):
        pipeline, _calls, _state = self._pipeline()

        result = pipeline.output_response(
            "Esta skill esta pronta e pertence a propria categoria.",
            False,
            direct_response_ready_announced=True,
        )

        self.assertEqual(
            result.styled_message,
            "Esta skill est\u00e1 pronta e pertence a pr\u00f3pria categoria.",
        )

    def test_output_response_polishes_general_conversation_terms(self):
        pipeline, _calls, _state = self._pipeline()

        result = pipeline.output_response(
            (
                "Meu nome e Axel. Recursao em Python e quando uma funcao chama ela mesma. "
                "Tesla pode ser a empresa de carros eletricos fundada por socios."
            ),
            False,
            direct_response_ready_announced=True,
        )

        self.assertIn("Meu nome é Axel.", result.styled_message)
        self.assertIn("Recursão em Python é quando uma função", result.styled_message)
        self.assertIn("carros elétricos", result.styled_message)
        self.assertIn("sócios", result.styled_message)

    def test_output_response_polishes_financial_climate_terms(self):
        pipeline, _calls, _state = self._pipeline()

        result = pipeline.output_response(
            (
                "El Nino pode afetar VGIA11 por tres caminhos: clima sobre safras, "
                "precos de commodities e juros/inflacao. No caso de VGIA11, eu olharia "
                "especialmente exposicao ao agro, qualidade dos devedores, garantias, "
                "inadimplencia, renegociacoes e estabilidade dos dividendos. "
                "Como o peso salvo e 16,7% da carteira, vale medir se esse risco e relevante "
                "no conjunto. Isso e leitura de risco, nao recomendacao de compra ou venda."
            ),
            False,
            direct_response_ready_announced=True,
        )

        self.assertIn("El Niño", result.styled_message)
        self.assertIn("três caminhos", result.styled_message)
        self.assertIn("preços de commodities", result.styled_message)
        self.assertIn("juros/inflação", result.styled_message)
        self.assertIn("exposição ao agro", result.styled_message)
        self.assertIn("inadimplência", result.styled_message)
        self.assertIn("renegociações", result.styled_message)
        self.assertIn("peso salvo é 16,7%", result.styled_message)
        self.assertIn("risco é relevante", result.styled_message)
        self.assertIn("Isso é leitura de risco, não recomendação", result.styled_message)

    def test_output_response_applies_personality_layer_after_styling(self):
        pipeline, calls, _state = self._pipeline(
            preferences={
                "assistant_personality_enabled": True,
                "assistant_humor_enabled": True,
                "assistant_humor_style": "seco",
                "assistant_humor_level": 2,
            }
        )

        result = pipeline.output_response(
            "Encontrei 4 versoes do arquivo final_final.pdf.",
            False,
            direct_response_ready_announced=True,
        )

        self.assertIn("Todas aparentemente definitivas.", result.styled_message)
        self.assertEqual(calls["terminal"], [f"IA: {result.styled_message}"])

    def test_execute_short_brain_mode_suppresses_personality_layer(self):
        pipeline, _calls, state = self._pipeline(
            preferences={
                "assistant_personality_enabled": True,
                "assistant_humor_enabled": True,
                "assistant_humor_style": "seco",
                "assistant_humor_level": 2,
            }
        )
        state.axel_brain_plan = {"response_mode": "execute_short", "risk_level": "low"}

        result = pipeline.output_response(
            "Encontrei 4 versoes do arquivo final_final.pdf.",
            False,
            direct_response_ready_announced=True,
        )

        self.assertNotIn("Todas aparentemente definitivas", result.styled_message)

    def test_output_response_trims_cutoff_final_fragment(self):
        pipeline, calls, _state = self._pipeline()

        result = pipeline.output_response(
            "Sim, senhor. A",
            True,
            direct_response_ready_announced=True,
        )

        self.assertEqual(result.styled_message, "Sim, senhor.")
        self.assertEqual(calls["speak"][0][0], ("Sim, senhor.",))

    def test_output_response_marks_incomplete_trailing_connector(self):
        pipeline, calls, _state = self._pipeline()

        result = pipeline.output_response(
            "A noite chegou, que tal salvar e.",
            True,
            direct_response_ready_announced=True,
        )

        self.assertEqual(result.styled_message, "A noite chegou, que tal salvar...")
        self.assertEqual(calls["speak"][0][0], ("A noite chegou, que tal salvar...",))

    def test_output_response_marks_incomplete_context_word(self):
        pipeline, calls, _state = self._pipeline()

        result = pipeline.output_response(
            "Que tal guardar o trabalho e ter uma boa.",
            True,
            direct_response_ready_announced=True,
        )

        self.assertEqual(result.styled_message, "Que tal guardar o trabalho e ter uma...")
        self.assertEqual(calls["speak"][0][0], ("Que tal guardar o trabalho e ter uma...",))

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
