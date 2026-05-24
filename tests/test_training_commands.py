import unittest
from unittest.mock import Mock, patch

import core.training_commands as training_commands
from core.training_commands import maybe_handle_training_command, reset_pending_training_request


class TrainingCommandTests(unittest.TestCase):
    def setUp(self):
        reset_pending_training_request()

    def test_today_workout_updates_snapshot(self):
        with (
            patch("core.training_commands.training_snapshot", return_value={"today": "push"}),
            patch("core.training_commands.update_ui_state") as update_ui,
            patch("core.training_commands.format_today_workout", return_value="Treino de hoje: Push."),
        ):
            result = maybe_handle_training_command("treino de hoje", Mock())

        self.assertEqual(result, "Treino de hoje: Push.")
        update_ui.assert_called_once_with({"training_snapshot": {"today": "push"}})

    def test_open_training_panel_uses_injected_ui_function(self):
        show_training = Mock(return_value="Painel aberto.")

        result = maybe_handle_training_command("abrir treino", show_training)

        self.assertEqual(result, "Painel aberto.")
        show_training.assert_called_once_with()

    def test_mark_completed_updates_snapshot(self):
        with (
            patch("core.training_commands.training_snapshot", return_value={"done": True}),
            patch("core.training_commands.update_ui_state") as update_ui,
            patch("core.training_commands.mark_training_completed", return_value="Treino marcado."),
        ):
            result = maybe_handle_training_command("treino concluido", Mock())

        self.assertEqual(result, "Treino marcado.")
        update_ui.assert_called_once_with({"training_snapshot": {"done": True}})

    def test_custom_training_sets_pending_when_muscles_missing(self):
        with (
            patch("core.training_commands.training_snapshot", return_value={}),
            patch("core.training_commands.update_ui_state"),
            patch("core.training_commands.mark_custom_training_from_text", return_value="Quais grupos voce treinou?"),
        ):
            result = maybe_handle_training_command("treinei ontem", Mock())

        self.assertEqual(result, "Quais grupos voce treinou?")
        self.assertEqual(training_commands.pending_training_request, "treinei ontem")

    def test_pending_training_request_consumes_muscle_reply(self):
        training_commands.pending_training_request = "treinei ontem"
        with (
            patch("core.training_commands.parse_muscles", return_value=["chest"]),
            patch("core.training_commands.training_snapshot", return_value={"logged": True}),
            patch("core.training_commands.update_ui_state") as update_ui,
            patch("core.training_commands.mark_custom_training_for_dates_from_text", return_value="Treino registrado.") as mark,
        ):
            result = maybe_handle_training_command("peito e triceps", Mock())

        self.assertEqual(result, "Treino registrado.")
        mark.assert_called_once_with("peito e triceps", "treinei ontem")
        self.assertEqual(training_commands.pending_training_request, "")
        update_ui.assert_called_once_with({"training_snapshot": {"logged": True}})

    def test_reminder_command_does_not_update_snapshot(self):
        with (
            patch("core.training_commands.set_training_reminder_from_text", return_value="Lembrete salvo.") as reminder,
            patch("core.training_commands.update_ui_state") as update_ui,
        ):
            result = maybe_handle_training_command("lembrete de treino 18h", Mock())

        self.assertEqual(result, "Lembrete salvo.")
        reminder.assert_called_once_with("lembrete de treino 18h")
        update_ui.assert_not_called()

    def test_unrelated_command_returns_none(self):
        self.assertIsNone(maybe_handle_training_command("abrir spotify", Mock()))


if __name__ == "__main__":
    unittest.main()
