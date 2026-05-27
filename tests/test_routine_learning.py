import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from memory import routine_learning


class RoutineLearningTests(unittest.TestCase):
    def test_observe_repeated_pair_creates_suggestion_after_threshold(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "routine_learning.json"
            with patch.object(routine_learning, "ROUTINE_LEARNING_PATH", path):
                suggestion = None
                for offset in range(3):
                    routine_learning.observe_routine_command("abrir chrome", {"intent": "open_app", "target": "chrome"}, now=100 + offset * 10)
                    suggestion = routine_learning.observe_routine_command(
                        "tocar spotify",
                        {"intent": "media_play_target", "target": "spotify"},
                        now=101 + offset * 10,
                    )

                self.assertIsNotNone(suggestion)
                self.assertIn("Criar rotina", suggestion["title"])
                self.assertEqual(len(routine_learning.pending_routine_suggestions()), 1)

    def test_ignored_intents_do_not_create_observations(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "routine_learning.json"
            with patch.object(routine_learning, "ROUTINE_LEARNING_PATH", path):
                suggestion = routine_learning.observe_routine_command("oi", {"intent": "respond", "response": "oi"}, now=1)

                self.assertIsNone(suggestion)
                self.assertEqual(routine_learning.load_routine_learning()["observations"], [])

    def test_format_pending_suggestions(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "routine_learning.json"
            with patch.object(routine_learning, "ROUTINE_LEARNING_PATH", path):
                for offset in range(3):
                    routine_learning.observe_routine_command("abrir chrome", {"intent": "open_app", "target": "chrome"}, now=100 + offset * 10)
                    routine_learning.observe_routine_command("tocar spotify", {"intent": "media_play_target", "target": "spotify"}, now=101 + offset * 10)

                self.assertIn("Sugestoes de rotina:", routine_learning.format_pending_routine_suggestions())


if __name__ == "__main__":
    unittest.main()
