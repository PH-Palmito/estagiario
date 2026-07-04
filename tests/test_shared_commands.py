import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.shared_commands import maybe_handle_shared_command


class SharedCommandsTests(unittest.TestCase):
    @patch("core.shared_commands.recent_execution_summary")
    def test_status_command_formats_recent_state(self, summary):
        summary.return_value = {
            "recent_errors": [],
            "no_match_routes": [],
            "slow_actions": [],
        }

        result = maybe_handle_shared_command("/status")

        self.assertIn("Status do Axel", result)
        self.assertIn("Sem erro recente", result)

    @patch("core.shared_commands.format_latency_report", return_value="Latencia do Axel: ok.")
    def test_usage_command_uses_latency_report(self, _latency):
        self.assertEqual(maybe_handle_shared_command("/usage"), "Latencia do Axel: ok.")

    def test_help_mentions_self_check_alias(self):
        result = maybe_handle_shared_command("/help")

        self.assertIn("/autoteste", result)
        self.assertIn("capacidades reais do axel", result)

    @patch("core.shared_commands.format_project_health_panel", return_value="Saude do Axel: projeto saudavel.")
    def test_health_command_uses_project_health_panel(self, health):
        result = maybe_handle_shared_command("check-up do axel")

        health.assert_called_once_with()
        self.assertEqual(result, "Saude do Axel: projeto saudavel.")

    @patch("core.shared_commands.run_axel_self_check", return_value="Autoteste rápido do Axel: 5/5 rotas essenciais OK.")
    def test_self_check_command_runs_smoke_check(self, self_check):
        result = maybe_handle_shared_command("/autoteste")

        self_check.assert_called_once_with()
        self.assertIn("5/5", result)

    @patch("core.shared_commands.format_pending_skill_suggestions", return_value="Sem sugestoes.")
    @patch("core.shared_commands.format_skill_catalog", return_value="Skills procedurais: estudos.")
    def test_skills_command_combines_catalog_and_pending(self, _catalog, _pending):
        result = maybe_handle_shared_command("/skills")

        self.assertIn("Skills procedurais", result)
        self.assertIn("Sem sugestoes", result)

    def test_real_capabilities_command_is_honest_about_partial_layers(self):
        result = maybe_handle_shared_command("capacidades reais do axel")

        self.assertIn("Capacidades reais do Axel", result)
        self.assertIn("Funcional", result)
        self.assertIn("Parcial", result)
        self.assertIn("Visual/organizacional", result)
        self.assertIn("Agentes especialistas", result)
        self.assertIn("Skills procedurais", result)
        self.assertIn("LED do teclado", result)
        self.assertIn("Primeira camada plugável", result)
        self.assertIn("não controla hardware físico", result)
        self.assertIn("App Windows", result)
        self.assertIn("Primeira camada por atalhos", result)
        self.assertIn("instalador final", result)
        self.assertIn("Regra prática", result)

    @patch("core.shared_commands.format_task_evaluation_summary", return_value="Autoavaliacao: ok.")
    @patch("core.shared_commands.format_capability_feedback", return_value="Feedback: ok.")
    @patch("core.shared_commands.format_axel_brain_insights", return_value="Insights: ok.")
    def test_insights_command_uses_runtime_history(self, _brain, _ranking, _eval):
        runtime = SimpleNamespace(axel_brain_history=[{"intent": "respond"}])

        result = maybe_handle_shared_command("/insights", runtime_state=runtime)

        self.assertIn("Insights: ok.", result)
        self.assertIn("Feedback: ok.", result)
        self.assertIn("Autoavaliacao: ok.", result)

    @patch("core.shared_commands.load_voice_preferences", return_value={"ai_text_provider": "local", "chat_model": "qwen"})
    def test_model_status_is_read_only(self, _prefs):
        result = maybe_handle_shared_command("/model")

        self.assertIn("provedor local", result)
        self.assertIn("qwen", result)

    @patch(
        "core.shared_commands.load_voice_preferences",
        return_value={
            "assistant_personality_enabled": True,
            "assistant_proactivity_enabled": False,
            "assistant_humor_enabled": True,
            "assistant_humor_style": "seco",
            "assistant_humor_level": 2,
        },
    )
    def test_personality_status_is_read_only(self, _prefs):
        result = maybe_handle_shared_command("/personalidade")

        self.assertIn("Personalidade do Axel: ligada", result)
        self.assertIn("Proatividade: desligada", result)

    @patch("core.shared_commands.load_learned_startup_phrases", return_value=("A mesa ja esta posta.",))
    def test_lists_learned_startup_phrases(self, _phrases):
        result = maybe_handle_shared_command("frases de inicializacao")

        self.assertIn("A mesa ja esta posta", result)

    def test_generate_startup_phrases_is_blocked_without_local_permission(self):
        result = maybe_handle_shared_command("gerar frases de inicializacao")

        self.assertIn("apenas para o canal local", result)

    @patch("core.shared_commands.generate_and_save_startup_phrases", return_value=["A mesa ja esta posta."])
    def test_generate_startup_phrases_runs_locally(self, generate):
        result = maybe_handle_shared_command("gerar frases de inicializacao", allow_state_changes=True)

        generate.assert_called_once_with("computer_startup")
        self.assertIn("A mesa ja esta posta", result)
        self.assertNotIn("..", result)

    @patch("core.shared_commands.generate_and_save_startup_phrases", return_value=["Salva o progresso antes de encerrar."])
    def test_generate_night_phrases_uses_night_category(self, generate):
        result = maybe_handle_shared_command("gerar frases noturnas", allow_state_changes=True)

        generate.assert_called_once_with("night_sleep_prompt")
        self.assertIn("aviso noturno", result)

    @patch(
        "core.shared_commands.generate_and_save_startup_phrases",
        side_effect=lambda category: [f"Frase pronta para {category}."],
    )
    def test_generate_all_phrase_categories_runs_each_category(self, generate):
        result = maybe_handle_shared_command("gerar frases do axel", allow_state_changes=True)

        called_categories = [call.args[0] for call in generate.call_args_list]
        self.assertIn("computer_startup", called_categories)
        self.assertIn("night_sleep_prompt", called_categories)
        self.assertIn("aviso noturno", result)

    @patch("core.shared_commands.load_ui_state", return_value={"llm_intent_judge_enabled": True})
    def test_intent_judge_status_is_read_only(self, _state):
        result = maybe_handle_shared_command("status do juiz de intencao")

        self.assertIn("Juiz LLM de intenção: ligado", result)

    def test_intent_judge_change_is_blocked_without_local_permission(self):
        result = maybe_handle_shared_command("ligar juiz llm")

        self.assertIn("só pode ser alterado no canal local", result)

    @patch("core.shared_commands.load_ui_state", return_value={"llm_intent_judge_enabled": True})
    @patch("core.shared_commands.update_ui_state")
    def test_intent_judge_change_updates_ui_state_when_local(self, update, _state):
        result = maybe_handle_shared_command("desligar juiz llm", allow_state_changes=True)

        update.assert_called_once_with({"llm_intent_judge_enabled": False})
        self.assertIn("desligado", result)

    def test_model_change_is_blocked_without_local_permission(self):
        result = maybe_handle_shared_command("/model local")

        self.assertIn("apenas no canal local", result)

    @patch("core.shared_commands.load_voice_preferences", return_value={"ai_text_provider": "local", "chat_model": "qwen"})
    @patch("core.shared_commands.update_voice_preferences")
    def test_model_change_updates_preferences_when_local(self, update, _prefs):
        refreshed = []

        result = maybe_handle_shared_command("/model nvidia", allow_state_changes=True, refresh_preferences=lambda: refreshed.append(True))

        update.assert_called_once()
        self.assertTrue(refreshed)
        self.assertIn("automatico", result.lower())

    def test_personality_change_is_blocked_without_local_permission(self):
        result = maybe_handle_shared_command("desligar personalidade")

        self.assertIn("so podem ser alteradas no canal local", result)

    @patch(
        "core.shared_commands.load_voice_preferences",
        return_value={
            "assistant_personality_enabled": False,
            "assistant_proactivity_enabled": True,
            "assistant_humor_enabled": False,
            "assistant_humor_style": "neutro",
            "assistant_humor_level": 0,
        },
    )
    @patch("core.shared_commands.update_voice_preferences")
    def test_personality_change_updates_preferences_when_local(self, update, _prefs):
        refreshed = []

        result = maybe_handle_shared_command(
            "ligar personalidade",
            allow_state_changes=True,
            refresh_preferences=lambda: refreshed.append(True),
        )

        update.assert_called_once_with({"assistant_personality_enabled": True})
        self.assertTrue(refreshed)
        self.assertIn("Personalidade ligada", result)

    def test_reset_runs_local_callbacks_only_when_allowed(self):
        calls = []

        blocked = maybe_handle_shared_command("/reset")
        allowed = maybe_handle_shared_command(
            "/reset",
            allow_state_changes=True,
            clear_chat=lambda: calls.append("chat"),
            reset_ui=lambda: calls.append("ui"),
        )

        self.assertIn("apenas no canal local", blocked)
        self.assertEqual(calls, ["chat", "ui"])
        self.assertIn("reiniciados", allowed)

    def test_stop_runs_local_callback_only_when_allowed(self):
        calls = []

        blocked = maybe_handle_shared_command("/stop")
        allowed = maybe_handle_shared_command("/stop", allow_state_changes=True, stop_pending=lambda: calls.append("stop"))

        self.assertIn("remoto limitado", blocked)
        self.assertEqual(calls, ["stop"])
        self.assertIn("Pendencias locais canceladas", allowed)

    def test_retry_uses_callback_when_available(self):
        result = maybe_handle_shared_command("/retry", retry_last=lambda: "Repeti.")

        self.assertEqual(result, "Repeti.")

    def test_retry_without_callback_is_honest(self):
        result = maybe_handle_shared_command("/retry")

        self.assertIn("Não encontrei", result)

    def test_undo_uses_callback_when_available(self):
        result = maybe_handle_shared_command("/undo", undo_last=lambda: "Cancelado.")

        self.assertEqual(result, "Cancelado.")

    def test_undo_without_callback_does_not_claim_execution_rollback(self):
        result = maybe_handle_shared_command("/undo")

        self.assertIn("nao vou fingir", result.lower())


if __name__ == "__main__":
    unittest.main()
