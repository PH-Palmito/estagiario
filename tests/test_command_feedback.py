import unittest
from types import SimpleNamespace

from core.command_feedback import action_progress_message, command_preview


class CommandFeedbackTests(unittest.TestCase):
    def test_static_progress_message(self):
        command = SimpleNamespace(action="image_analyze")

        self.assertEqual(
            action_progress_message(command, next_phrase=lambda _key, _options: "unused", variants={}),
            "Analisando a imagem...",
        )

    def test_variant_progress_message_uses_next_phrase(self):
        calls = []

        def next_phrase(key, options):
            calls.append((key, options))
            return options[0]

        command = SimpleNamespace(action="browser_search_site")
        result = action_progress_message(
            command,
            next_phrase=next_phrase,
            variants={"browser_search_site": ("Buscando...",)},
        )

        self.assertEqual(result, "Buscando...")
        self.assertEqual(calls, [("progress_browser_search_site", ("Buscando...",))])

    def test_missing_progress_message_returns_none(self):
        command = SimpleNamespace(action="unknown")

        self.assertIsNone(action_progress_message(command, next_phrase=lambda _key, _options: "", variants={}))

    def test_command_preview_formats_action_and_params(self):
        command = SimpleNamespace(action="open_app", params={"target": "chrome", "mode": "new", "extra": 1, "ignored": 2})

        self.assertEqual(command_preview(command), "open_app (target=chrome, mode=new, extra=1)")

    def test_command_preview_handles_empty_or_unknown_command(self):
        self.assertEqual(command_preview(None), "")
        self.assertEqual(command_preview(SimpleNamespace(action="pause", params={})), "pause")
        self.assertEqual(command_preview({"intent": "respond"}), "{'intent': 'respond'}")


if __name__ == "__main__":
    unittest.main()
