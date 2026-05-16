import unittest

from core.app_bootstrap import HELP_TEXT, parse_app_flags


class AppBootstrapTests(unittest.TestCase):
    def test_parse_voice_hotword_ui_flags(self):
        flags = parse_app_flags(["main.py", "--voice", "--hotword", "--ui"])

        self.assertTrue(flags.voice_mode)
        self.assertTrue(flags.hotword_mode)
        self.assertTrue(flags.ui_mode)
        self.assertFalse(flags.help_requested)

    def test_parse_audio_diagnostic_seconds(self):
        flags = parse_app_flags(["main.py", "--audio-test", "2.5"])

        self.assertTrue(flags.audio_diagnostic_requested)
        self.assertEqual(flags.audio_diagnostic_seconds, 2.5)

    def test_parse_startup_defer_briefing(self):
        flags = parse_app_flags(["main.py", "--voice", "--startup"])

        self.assertTrue(flags.startup_mode)
        self.assertTrue(flags.defer_startup_briefing)

    def test_parse_startup_no_defer_briefing(self):
        flags = parse_app_flags(["main.py", "--startup", "--no-defer-startup-briefing"])

        self.assertTrue(flags.startup_mode)
        self.assertFalse(flags.defer_startup_briefing)

    def test_help_text_is_ascii_and_mentions_main_flags(self):
        HELP_TEXT.encode("ascii")
        self.assertIn("--voice", HELP_TEXT)
        self.assertIn("--audio-test", HELP_TEXT)


if __name__ == "__main__":
    unittest.main()
