import unittest
from unittest.mock import patch

from core.command_schema import Command
from core.command_service import command_permission_payload, execute_processed_command, process_raw_action, should_auto_background
from core.action_result import ActionResult


class FakeRuntimeState:
    def __init__(self):
        self.updated = []

    def update(self, command, result):
        self.updated.append((command, result))


class CommandServiceTests(unittest.TestCase):
    def test_process_raw_action_rejects_non_dict(self):
        events = []

        result = process_raw_action("abrir spotify", FakeRuntimeState(), lambda event, **payload: events.append((event, payload)))

        self.assertEqual(result, "Acao invalida.")
        self.assertEqual(events[0][0], "action_invalid")

    def test_process_raw_action_validates_command(self):
        events = []

        result = process_raw_action(
            {"intent": "weather_summary", "target": "Salvador"},
            FakeRuntimeState(),
            lambda event, **payload: events.append((event, payload)),
        )

        self.assertIsInstance(result, Command)
        self.assertEqual(result.action, "weather_summary")
        self.assertEqual(result.params, {"location": "Salvador"})
        self.assertIn("action_processed", [event for event, _payload in events])
        processed_payload = events[-1][1]
        self.assertEqual(processed_payload["risk_level"], "read")
        self.assertTrue(processed_payload["read_only"])

    def test_execute_processed_command_updates_state_and_logs(self):
        state = FakeRuntimeState()
        events = []
        command = Command(action="respond", params={"message": "ok"})

        result = execute_processed_command(
            command,
            state,
            lambda executed: executed.params["message"],
            lambda event, **payload: events.append((event, payload)),
        )

        self.assertEqual(result, "ok")
        self.assertEqual(state.updated, [(command, "ok")])
        self.assertEqual(
            [event for event, _payload in events],
            ["command_execute_start", "command_execute_end", "latency_stage"],
        )
        self.assertTrue(events[-2][1]["success"])
        self.assertIn("risk_level", events[0][1])
        self.assertIn("requires_confirmation", events[-2][1])
        self.assertEqual(events[-1][1]["stage"], "action")

    def test_execute_processed_command_auto_backgrounds_safe_heavy_action(self):
        state = FakeRuntimeState()
        events = []
        command = Command(action="daily_briefing", params={})

        with patch("core.background_tasks.submit_background_task", return_value="bg-42") as submit:
            result = execute_processed_command(
                command,
                state,
                lambda _executed: "briefing pronto",
                lambda event, **payload: events.append((event, payload)),
            )

        self.assertEqual(result, "Deixei daily_briefing rodando em segundo plano. Tarefa: bg-42.")
        self.assertEqual(state.updated, [(command, result)])
        self.assertEqual(events[0][0], "command_performance_advice")
        self.assertEqual(events[0][1]["mode"], "background_with_cache")
        self.assertEqual(events[1][0], "command_auto_background")
        submit.assert_called_once()

    def test_should_auto_background_rejects_sensitive_action(self):
        command = Command(action="windows_startup_disable", params={})

        self.assertFalse(should_auto_background(command))

    def test_should_auto_background_accepts_safe_vision_action(self):
        command = Command(action="image_analyze_screen", params={})

        self.assertTrue(should_auto_background(command))

    def test_execute_processed_command_normalizes_action_result(self):
        state = FakeRuntimeState()
        events = []
        command = Command(action="respond", params={"message": "ok"})

        result = execute_processed_command(
            command,
            state,
            lambda _executed: ActionResult.failed("nao deu", error="unit failure"),
            lambda event, **payload: events.append((event, payload)),
        )

        self.assertEqual(result, "nao deu")
        self.assertEqual(state.updated, [(command, "nao deu")])
        self.assertFalse(events[-2][1]["success"])
        self.assertEqual(events[-2][1]["error"], "unit failure")
        self.assertEqual(events[-1][1]["stage"], "action")

    def test_command_permission_payload_describes_registered_command(self):
        command = Command(action="file_delete", params={"path": "x"}, requires_confirmation=True)

        payload = command_permission_payload(command)

        self.assertEqual(payload["risk_level"], "critical")
        self.assertTrue(payload["requires_confirmation"])
        self.assertEqual(payload["sandbox_scope"], "filesystem")
        self.assertTrue(payload["dry_run_recommended"])
        self.assertTrue(payload["requires_strong_confirmation"])


if __name__ == "__main__":
    unittest.main()
