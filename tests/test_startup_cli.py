import unittest
from types import SimpleNamespace

from core.startup_cli import (
    handle_audio_diagnostic_cli,
    handle_voice_tools_cli,
    handle_windows_startup_cli,
)


class StartupCliTests(unittest.TestCase):
    def test_handles_windows_startup_enable(self):
        printed = []

        handled = handle_windows_startup_cli(
            ["main.py", "--enable-startup"],
            print_fn=printed.append,
            enable_windows_startup=lambda: "enabled",
            disable_windows_startup=lambda: "disabled",
            windows_startup_status=lambda: "status",
        )

        self.assertTrue(handled)
        self.assertEqual(printed, ["enabled"])

    def test_lists_piper_voices(self):
        printed = []

        handled = self._handle_voice(
            ["main.py", "--list-piper-voices"],
            print_fn=printed.append,
            list_piper_voices=lambda: [{"key": "pt", "installed": True, "label": "PT"}],
        )

        self.assertTrue(handled)
        self.assertEqual(printed, ["Vozes Piper disponiveis:", "- pt (instalada) - PT"])

    def test_applies_voice_profile_and_refreshes_preferences(self):
        refreshed = []
        printed = []

        handled = self._handle_voice(
            ["main.py", "--voice-profile", "jarvis"],
            print_fn=printed.append,
            apply_voice_profile=lambda name: (True, f"applied:{name}"),
            refresh_voice_preferences=lambda: refreshed.append(True),
        )

        self.assertTrue(handled)
        self.assertEqual(printed, ["applied:jarvis"])
        self.assertEqual(refreshed, [True])

    def test_voice_test_uses_inline_text_and_waits_for_playback(self):
        preferences = {}
        responses = []
        waited = []

        handled = self._handle_voice(
            ["main.py", "--voice-test", "ola", "chefe"],
            voice_preferences=preferences,
            output_response=lambda *args, **kwargs: responses.append((args, kwargs)),
            set_windows_voice_wait_for_playback=lambda: waited.append(True),
        )

        self.assertTrue(handled)
        self.assertTrue(preferences["tts_wait_for_playback"])
        self.assertEqual(responses[0], (("ola chefe",), {"voice_mode": True}))
        self.assertEqual(waited, [True])

    def test_audio_diagnostic_cli(self):
        printed = []

        handled = handle_audio_diagnostic_cli(
            requested=True,
            seconds=2.5,
            run_audio_diagnostic=lambda seconds: f"audio:{seconds}",
            print_fn=printed.append,
        )

        self.assertTrue(handled)
        self.assertEqual(
            printed,
            ["Gravando diagnostico de audio. Fale uma frase curta...", "audio:2.5"],
        )

    def _handle_voice(self, argv, **overrides):
        params = {
            "voice_preferences": {},
            "common_tts_cache_phrases": lambda: ["oi"],
            "prime_piper_cache": lambda phrases: SimpleNamespace(text="ok", error=""),
            "list_piper_voices": lambda: [],
            "download_piper_voice": lambda name: (True, f"download:{name}"),
            "apply_piper_voice": lambda name: (True, f"voice:{name}"),
            "list_voice_profiles": lambda: [],
            "apply_voice_profile": lambda name: (True, f"profile:{name}"),
            "refresh_voice_preferences": lambda: None,
            "output_response": lambda *args, **kwargs: None,
            "print_fn": lambda value: None,
            "set_windows_voice_wait_for_playback": lambda: None,
        }
        params.update(overrides)
        return handle_voice_tools_cli(argv, **params)


if __name__ == "__main__":
    unittest.main()
