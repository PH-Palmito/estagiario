import unittest

from core.app_runtime import AppRuntime
from core.runtime_state import RuntimeState
from core.terminal_voice_io import TerminalVoiceIO


class AppRuntimeTests(unittest.TestCase):
    def test_initializes_runtime_state_and_terminal_io(self):
        runtime = AppRuntime(ui_history_max_items=12)

        self.assertIsInstance(runtime.runtime_state, RuntimeState)
        self.assertIsInstance(runtime.terminal_io, TerminalVoiceIO)
        self.assertEqual(runtime.terminal_io.ui_history_max_items, 12)

    def test_service_slots_start_empty(self):
        runtime = AppRuntime()

        self.assertIsNone(runtime.ui_runtime)
        self.assertIsNone(runtime.improvement_brain)
        self.assertIsNone(runtime.reminder_announcer)
        self.assertIsNone(runtime.response_pipeline)


if __name__ == "__main__":
    unittest.main()
