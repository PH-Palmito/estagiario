import unittest

from core.cli_args import cli_text_after, cli_value_after


class CliArgsTests(unittest.TestCase):
    def test_cli_value_after_returns_next_arg(self):
        self.assertEqual(cli_value_after(["main.py", "--voice-profile", "jarvis"], "--voice-profile"), "jarvis")

    def test_cli_value_after_rejects_missing_empty_or_next_flag(self):
        self.assertIsNone(cli_value_after(["main.py"], "--voice-profile"))
        self.assertIsNone(cli_value_after(["main.py", "--voice-profile"], "--voice-profile"))
        self.assertIsNone(cli_value_after(["main.py", "--voice-profile", "--ui"], "--voice-profile"))
        self.assertIsNone(cli_value_after(["main.py", "--voice-profile", ""], "--voice-profile"))

    def test_cli_text_after_collects_until_next_flag(self):
        self.assertEqual(
            cli_text_after(["main.py", "--voice-test", "ola", "chefe", "--ui"], "--voice-test"),
            "ola chefe",
        )

    def test_cli_text_after_returns_none_for_empty_or_missing(self):
        self.assertIsNone(cli_text_after(["main.py"], "--voice-test"))
        self.assertIsNone(cli_text_after(["main.py", "--voice-test", "--ui"], "--voice-test"))


if __name__ == "__main__":
    unittest.main()
