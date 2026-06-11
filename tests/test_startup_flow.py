import unittest
from types import SimpleNamespace

from core.startup_flow import StartupFlowHandlers, run_startup_flow


class StartupFlowTests(unittest.TestCase):
    def _handlers(self, calls, **overrides):
        handlers = {
            "handle_startup_cli": lambda flags: calls.append(("cli", flags)) or False,
            "initialize_runtime_services": lambda ui_mode: calls.append(("init", ui_mode)),
            "announce_voice_startup": lambda **kwargs: calls.append(("voice", kwargs)),
            "refresh_ui_runtime_state": lambda: calls.append("refresh"),
            "send_startup_briefing": lambda voice_mode: calls.append(("briefing", voice_mode)) or True,
        }
        handlers.update(overrides)
        return StartupFlowHandlers(**handlers)

    def test_stops_when_startup_cli_handles(self):
        calls = []
        flags = SimpleNamespace(defer_startup_briefing=False)

        should_continue = run_startup_flow(
            flags=flags,
            voice_mode=True,
            hotword_mode=True,
            ui_mode=True,
            defer_startup_briefing=False,
            handlers=self._handlers(calls, handle_startup_cli=lambda value: calls.append(("cli", value)) or True),
        )

        self.assertFalse(should_continue)
        self.assertEqual(calls, [("cli", flags)])

    def test_initializes_and_announces_voice_before_refresh(self):
        calls = []
        flags = SimpleNamespace(defer_startup_briefing=True)

        should_continue = run_startup_flow(
            flags=flags,
            voice_mode=True,
            hotword_mode=False,
            ui_mode=True,
            defer_startup_briefing=True,
            handlers=self._handlers(calls),
        )

        self.assertTrue(should_continue)
        self.assertEqual(
            calls,
            [
                ("cli", flags),
                ("init", True),
                ("voice", {"hotword_mode": False, "defer_startup_briefing": True}),
                "refresh",
            ],
        )

    def test_sends_startup_briefing_when_only_ui_is_enabled(self):
        calls = []
        flags = SimpleNamespace(defer_startup_briefing=False, startup_mode=False)

        should_continue = run_startup_flow(
            flags=flags,
            voice_mode=False,
            hotword_mode=False,
            ui_mode=True,
            defer_startup_briefing=False,
            handlers=self._handlers(calls),
        )

        self.assertTrue(should_continue)
        self.assertEqual(calls, [("cli", flags), ("init", True), ("briefing", False), "refresh"])

    def test_skips_voice_and_briefing_when_plain_text_mode_is_disabled(self):
        calls = []
        flags = SimpleNamespace(defer_startup_briefing=False, startup_mode=False)

        should_continue = run_startup_flow(
            flags=flags,
            voice_mode=False,
            hotword_mode=False,
            ui_mode=False,
            defer_startup_briefing=False,
            handlers=self._handlers(calls),
        )

        self.assertTrue(should_continue)
        self.assertEqual(calls, [("cli", flags), ("init", False), "refresh"])

    def test_sends_startup_briefing_for_startup_mode_without_voice(self):
        calls = []
        flags = SimpleNamespace(defer_startup_briefing=True, startup_mode=True)

        should_continue = run_startup_flow(
            flags=flags,
            voice_mode=False,
            hotword_mode=False,
            ui_mode=False,
            defer_startup_briefing=True,
            handlers=self._handlers(calls),
        )

        self.assertTrue(should_continue)
        self.assertEqual(calls, [("cli", flags), ("init", False), ("briefing", False), "refresh"])


if __name__ == "__main__":
    unittest.main()
