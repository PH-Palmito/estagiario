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

    @patch("core.shared_commands.format_pending_skill_suggestions", return_value="Sem sugestoes.")
    @patch("core.shared_commands.format_skill_catalog", return_value="Skills procedurais: estudos.")
    def test_skills_command_combines_catalog_and_pending(self, _catalog, _pending):
        result = maybe_handle_shared_command("/skills")

        self.assertIn("Skills procedurais", result)
        self.assertIn("Sem sugestoes", result)

    @patch("core.shared_commands.format_task_evaluation_summary", return_value="Autoavaliacao: ok.")
    @patch("core.shared_commands.format_capability_rankings", return_value="Ranking: ok.")
    @patch("core.shared_commands.format_axel_brain_insights", return_value="Insights: ok.")
    def test_insights_command_uses_runtime_history(self, _brain, _ranking, _eval):
        runtime = SimpleNamespace(axel_brain_history=[{"intent": "respond"}])

        result = maybe_handle_shared_command("/insights", runtime_state=runtime)

        self.assertIn("Insights: ok.", result)
        self.assertIn("Ranking: ok.", result)
        self.assertIn("Autoavaliacao: ok.", result)

    @patch("core.shared_commands.load_voice_preferences", return_value={"ai_text_provider": "local", "chat_model": "qwen"})
    def test_model_status_is_read_only(self, _prefs):
        result = maybe_handle_shared_command("/model")

        self.assertIn("provedor local", result)
        self.assertIn("qwen", result)

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

        self.assertIn("Nao encontrei", result)

    def test_undo_uses_callback_when_available(self):
        result = maybe_handle_shared_command("/undo", undo_last=lambda: "Cancelado.")

        self.assertEqual(result, "Cancelado.")

    def test_undo_without_callback_does_not_claim_execution_rollback(self):
        result = maybe_handle_shared_command("/undo")

        self.assertIn("nao vou fingir", result.lower())


if __name__ == "__main__":
    unittest.main()
