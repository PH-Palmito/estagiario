import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main


class MainVoiceRuntimeTests(unittest.TestCase):
    def test_wait_for_hotword_uses_current_ui_state_for_idle_sleep(self):
        calls = {}

        def fake_wait_for_hotword(**kwargs):
            calls["delay"] = kwargs["idle_sleep_seconds"]()
            return True, False, ""

        terminal_io = SimpleNamespace(wait_for_hotword=fake_wait_for_hotword)

        with (
            patch.object(main.app_runtime, "terminal_io", terminal_io),
            patch.object(main, "load_ui_state", return_value={"performance_mode": "economy"}),
        ):
            result = main.wait_for_hotword(True, True, False)

        self.assertEqual(result, (True, False, ""))
        self.assertGreater(calls["delay"], 0.08)


if __name__ == "__main__":
    unittest.main()
