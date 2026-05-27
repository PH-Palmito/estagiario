import unittest
from types import SimpleNamespace
from unittest.mock import patch

import main


class MainStartupFlowTests(unittest.TestCase):
    def test_handle_startup_cli_short_circuits_in_order(self):
        calls = []
        flags = SimpleNamespace()

        with (
            patch.object(main, "handle_windows_startup_cli", side_effect=lambda: calls.append("windows") or False),
            patch.object(main, "handle_voice_profile_cli", side_effect=lambda: calls.append("voice") or True),
            patch.object(main, "handle_audio_diagnostic_cli", side_effect=lambda _flags: calls.append("audio") or False),
        ):
            self.assertTrue(main.handle_startup_cli(flags))

        self.assertEqual(calls, ["windows", "voice"])

    def test_initialize_runtime_services_starts_ui_only_when_requested(self):
        calls = []

        with (
            patch.object(main, "clear", side_effect=lambda: calls.append("clear")),
            patch.object(main, "reset_ui_state", side_effect=lambda: calls.append("reset_ui")),
            patch.object(main, "refresh_ui_runtime_state", side_effect=lambda patch=None: calls.append(("refresh", patch))),
            patch.object(main, "refresh_improvement_brain", side_effect=lambda force=False: calls.append(("brain", force))),
            patch.object(main, "start_background_investment_refresh_loop", side_effect=lambda: calls.append("investments")),
            patch.object(main, "show_ui_hud", side_effect=lambda: calls.append("hud")),
        ):
            main.initialize_runtime_services(ui_mode=True)

        self.assertEqual(
            calls,
            [
                "clear",
                "reset_ui",
                ("refresh", {"visible": False}),
                ("brain", True),
                "investments",
                "hud",
            ],
        )

    def test_announce_voice_startup_can_defer_briefing(self):
        calls = []

        with (
            patch.dict(main.VOICE_PREFERENCES, {"startup_voice_greeting_enabled": True}, clear=True),
            patch.object(main, "output_response", side_effect=lambda *args, **kwargs: calls.append(("output", args, kwargs))),
            patch.object(main, "set_voice_status", side_effect=lambda status: calls.append(("status", status))),
            patch.object(main, "startup_greeting_message", return_value="Pronto."),
            patch.object(main, "warm_common_tts_cache_async", side_effect=lambda: calls.append("warm")),
            patch.object(main, "schedule_startup_briefing_async", side_effect=lambda voice_mode: calls.append(("defer", voice_mode))),
            patch.object(main, "maybe_send_startup_briefing", side_effect=lambda voice_mode: calls.append(("briefing", voice_mode))),
        ):
            main.announce_voice_startup(hotword_mode=False, defer_startup_briefing=True)

        self.assertEqual(calls[0][0], "output")
        self.assertEqual(calls[1], ("output", ("Pronto.",), {"voice_mode": True}))
        self.assertIn("warm", calls)
        self.assertIn(("defer", True), calls)
        self.assertNotIn(("briefing", True), calls)


if __name__ == "__main__":
    unittest.main()
