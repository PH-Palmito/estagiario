import unittest
from unittest.mock import patch

from actions import ActionSpec, ensure_default_actions, register_action
from actions.background_actions import (
    background_daily_briefing,
    background_investment_refresh,
    background_latest_result,
    background_notifications,
    background_status,
    background_vision_screen,
    run_action_in_background,
)


class BackgroundActionTests(unittest.TestCase):
    def test_background_status_formats_summary(self):
        with patch(
            "actions.background_actions.background_task_summary",
            return_value={
                "running": 1,
                "succeeded": 2,
                "failed": 0,
                "latest": {"name": "briefing", "status": "succeeded"},
            },
        ):
            result = background_status({})

        self.assertIn("1 rodando", result)
        self.assertIn("2 concluidas", result)
        self.assertIn("ultima briefing (succeeded)", result)

    def test_background_latest_result_formats_success(self):
        with patch(
            "actions.background_actions.latest_background_task_result",
            return_value={
                "task_id": "bg-1",
                "name": "daily_briefing",
                "status": "succeeded",
                "duration_ms": 123,
                "message": "Resumo pronto",
            },
        ):
            result = background_latest_result({})

        self.assertIn("daily_briefing (bg-1) concluida em 123 ms", result)
        self.assertIn("Resumo pronto", result)

    def test_background_latest_result_formats_failure(self):
        with patch(
            "actions.background_actions.latest_background_task_result",
            return_value={"task_id": "bg-2", "name": "visao", "status": "failed", "error": "boom"},
        ):
            result = background_latest_result({})

        self.assertIn("visao (bg-2) falhou", result)
        self.assertIn("boom", result)

    def test_background_notifications_consumes_pending_items(self):
        with (
            patch(
                "actions.background_actions.consume_background_notifications",
                return_value=[
                    {"name": "daily_briefing", "status": "succeeded", "message": "ok"},
                    {"name": "visao", "status": "failed", "error": "boom"},
                ],
            ),
            patch("memory.ui_state.append_ui_notification") as notify_mock,
        ):
            result = background_notifications({})

        self.assertIn("daily_briefing terminou: ok", result)
        self.assertIn("visao falhou: boom", result)
        notify_mock.assert_called_once()

    def test_run_action_in_background_submits_task(self):
        submitted = []

        with patch(
            "actions.background_actions.submit_background_task",
            side_effect=lambda name, func: submitted.append((name, func)) or "bg-9",
        ):
            result = run_action_in_background("daily_briefing", {})

        self.assertEqual(result, "Deixei daily_briefing rodando em segundo plano. Tarefa: bg-9.")
        self.assertEqual(submitted[0][0], "daily_briefing")

    def test_background_daily_briefing_uses_daily_briefing_action(self):
        with patch("actions.background_actions.run_action_in_background", return_value="ok") as run_mock:
            result = background_daily_briefing({})

        self.assertEqual(result, "ok")
        run_mock.assert_called_once_with("daily_briefing", {})

    def test_run_action_in_background_rejects_recursive_background_action(self):
        result = run_action_in_background("background.run_action", {})

        self.assertIn("Nao executo", result)

    def test_generic_background_rejects_sensitive_action(self):
        register_action(
            ActionSpec(
                name="unit.sensitive_background",
                description="Teste sensivel.",
                handler=lambda _args: "ok",
                read_only=False,
                requires_confirmation=True,
            )
        )

        result = run_action_in_background("unit.sensitive_background", {})

        self.assertIn("precisa de confirmacao", result)

    def test_background_wrappers_submit_expected_actions(self):
        ensure_default_actions()
        submitted = []

        with patch(
            "actions.background_actions.submit_background_task",
            side_effect=lambda name, func: submitted.append((name, func)) or f"bg-{len(submitted)}",
        ):
            vision_result = background_vision_screen({})
            refresh_result = background_investment_refresh({})

        self.assertIn("image_analyze_screen", vision_result)
        self.assertIn("investment_refresh_public_wallet", refresh_result)
        self.assertEqual([item[0] for item in submitted], ["image_analyze_screen", "investment_refresh_public_wallet"])


if __name__ == "__main__":
    unittest.main()
