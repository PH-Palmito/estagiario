import unittest

from core.command_schema import Command
from core.command_service import execute_processed_command, process_raw_action


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
        self.assertEqual([event for event, _payload in events], ["command_execute_start", "command_execute_end"])


if __name__ == "__main__":
    unittest.main()
