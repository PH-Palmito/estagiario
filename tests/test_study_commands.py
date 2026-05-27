import unittest
from unittest.mock import Mock, patch

from core.study_commands import maybe_handle_study_command


class StudyCommandTests(unittest.TestCase):
    def test_open_study_panel_refreshes_ui_snapshot(self):
        show_hud = Mock(return_value="hud")
        with (
            patch("core.study_commands.study_snapshot", return_value={"minutes_today": 10}),
            patch("core.study_commands.update_ui_state") as update_ui,
        ):
            result = maybe_handle_study_command("painel de estudos", show_hud)

        self.assertEqual(result, "Painel de estudos aberto.")
        show_hud.assert_called_once_with()
        update_ui.assert_called_once_with(
            {
                "study_snapshot": {"minutes_today": 10},
                "active_panel": "estudos",
                "open_panels": ["estudos"],
            }
        )

    def test_logs_study_session(self):
        with (
            patch("core.study_commands.log_study_session", return_value="registrado") as log,
            patch("core.study_commands.study_snapshot", return_value={}),
            patch("core.study_commands.update_ui_state"),
        ):
            result = maybe_handle_study_command("estudei Python 30 minutos", Mock())

        self.assertEqual(result, "registrado")
        log.assert_called_once_with("estudei Python 30 minutos")

    def test_unrelated_command_returns_none(self):
        self.assertIsNone(maybe_handle_study_command("abrir spotify", Mock()))


if __name__ == "__main__":
    unittest.main()
