import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import study


class StudyMemoryTests(unittest.TestCase):
    def test_study_goals_reviews_and_sessions_feed_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "study.json"
            with (
                patch.object(study, "STUDY_PATH", path),
                patch.object(study, "sync_memory_state_safely"),
            ):
                goal = study.add_study_goal("meta de estudo terminar modulo de React")
                review = study.add_study_review("amanha as 10h hooks do React")
                session = study.log_study_session("estudei React 35 minutos")
                snapshot = study.study_snapshot()

        self.assertIn("terminar modulo de React", goal)
        self.assertIn("Revisao registrada", review)
        self.assertIn("35 min", session)
        self.assertEqual(snapshot["minutes_today"], 35)
        self.assertEqual(snapshot["goals"][0]["text"], "terminar modulo de React")
        self.assertEqual(snapshot["pending_reviews"][0]["text"], "hooks do React")

    def test_complete_study_review_marks_first_pending(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "study.json"
            with (
                patch.object(study, "STUDY_PATH", path),
                patch.object(study, "sync_memory_state_safely"),
            ):
                study.add_study_review("amanha revisar flashcards")
                result = study.complete_study_review("1")
                snapshot = study.study_snapshot()

        self.assertIn("Revisao concluida", result)
        self.assertEqual(snapshot["pending_reviews"], [])


if __name__ == "__main__":
    unittest.main()
