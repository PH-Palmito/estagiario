import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from memory import skill_learning


class SkillLearningTests(unittest.TestCase):
    def test_repeated_pattern_creates_skill_suggestion(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill_learning.json"
            with patch.object(skill_learning, "SKILL_LEARNING_PATH", path):
                suggestion = None
                for offset in range(4):
                    suggestion = skill_learning.observe_skill_opportunity(
                        "revisar codigo e rodar testes",
                        {"intent": "respond_code_review"},
                        toolset="programacao",
                        agent="dev_agent",
                        now=100 + offset,
                    )

                self.assertIsNotNone(suggestion)
                self.assertIn("skill", suggestion["title"].lower())
                self.assertEqual(len(skill_learning.pending_skill_suggestions()), 1)

    def test_ignored_intent_does_not_create_observation(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill_learning.json"
            with patch.object(skill_learning, "SKILL_LEARNING_PATH", path):
                suggestion = skill_learning.observe_skill_opportunity(
                    "oi",
                    {"intent": "respond"},
                    toolset="voz_rapida",
                    agent="voice_agent",
                    now=1,
                )

                self.assertIsNone(suggestion)
                self.assertEqual(skill_learning.load_skill_learning()["observations"], [])

    def test_format_pending_skill_suggestions(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill_learning.json"
            with patch.object(skill_learning, "SKILL_LEARNING_PATH", path):
                for offset in range(4):
                    skill_learning.observe_skill_opportunity(
                        "analisar dividendos da carteira",
                        {"intent": "investment_news"},
                        toolset="carteira",
                        agent="investment_agent",
                        now=200 + offset,
                    )

                self.assertIn("Sugestoes de skills:", skill_learning.format_pending_skill_suggestions())

    def test_approve_pending_skill_suggestion_creates_skill(self):
        with TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            path = root / "skill_learning.json"
            skills_dir = root / "skills"
            with (
                patch.object(skill_learning, "SKILL_LEARNING_PATH", path),
                patch("memory.skill_learning.upsert_skill_from_suggestion") as upsert,
            ):
                upsert.side_effect = lambda suggestion: skills_dir / str(suggestion["toolset"]) / "SKILL.md"
                for offset in range(4):
                    skill_learning.observe_skill_opportunity(
                        "revisar codigo e rodar testes",
                        {"intent": "respond_code_review"},
                        toolset="programacao",
                        agent="dev_agent",
                        now=300 + offset,
                    )

                result = skill_learning.approve_pending_skill_suggestion()
                state = skill_learning.load_skill_learning()

        self.assertIn("Skill procedural aprovada", result)
        self.assertEqual(state["suggestions"][0]["status"], "approved")
        self.assertEqual(skill_learning.pending_skill_suggestions(), [])

    def test_reject_pending_skill_suggestion_marks_rejected(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill_learning.json"
            with patch.object(skill_learning, "SKILL_LEARNING_PATH", path):
                for offset in range(4):
                    skill_learning.observe_skill_opportunity(
                        "analisar dividendos da carteira",
                        {"intent": "investment_news"},
                        toolset="carteira",
                        agent="investment_agent",
                        now=400 + offset,
                    )

                result = skill_learning.reject_pending_skill_suggestion()
                state = skill_learning.load_skill_learning()

        self.assertEqual(result, "Sugestao de skill rejeitada.")
        self.assertEqual(state["suggestions"][0]["status"], "rejected")
        self.assertEqual(skill_learning.pending_skill_suggestions(), [])


if __name__ == "__main__":
    unittest.main()
