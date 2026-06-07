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

    def test_suggestion_uses_specific_skill_name_from_intent(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill_learning.json"
            with patch.object(skill_learning, "SKILL_LEARNING_PATH", path):
                suggestion = None
                for offset in range(4):
                    suggestion = skill_learning.observe_skill_opportunity(
                        "iniciar bot telegram",
                        {"intent": "telegram.start_bot"},
                        toolset="sistema",
                        agent="system_agent",
                        now=150 + offset,
                    )

                self.assertIsNotNone(suggestion)
                self.assertEqual(suggestion["skill_name"], "telegram-start-bot")
                self.assertIn("telegram start bot", suggestion["title"])

    def test_similar_action_words_share_one_skill_suggestion(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill_learning.json"
            with patch.object(skill_learning, "SKILL_LEARNING_PATH", path):
                for offset, text in enumerate(
                    [
                        "iniciar bot telegram",
                        "ativar bot telegram",
                        "iniciar bot telegram",
                        "ativar bot telegram",
                    ]
                ):
                    skill_learning.observe_skill_opportunity(
                        text,
                        {"intent": "telegram.start_bot"},
                        toolset="sistema",
                        agent="system_agent",
                        now=180 + offset,
                    )

                suggestions = skill_learning.pending_skill_suggestions()

            self.assertEqual(len(suggestions), 1)
            self.assertEqual(suggestions[0]["skill_name"], "telegram-start-bot")
            self.assertIn("iniciar bot telegram", suggestions[0]["examples"])
            self.assertIn("ativar bot telegram", suggestions[0]["examples"])

    def test_pending_suggestions_enrich_legacy_generic_titles(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "skill_learning.json"
            path.write_text(
                """
                {
                  "suggestions": [
                    {
                      "pattern_id": "abc",
                      "title": "Criar skill de sistema",
                      "reason": "Padrao procedural apareceu 4 vezes para system_agent.",
                      "toolset": "sistema",
                      "agent": "system_agent",
                      "intent": "telegram.start_bot",
                      "examples": ["iniciar bot telegram"],
                      "status": "suggested",
                      "created_at": 10
                    }
                  ]
                }
                """,
                encoding="utf-8",
            )
            with patch.object(skill_learning, "SKILL_LEARNING_PATH", path):
                suggestions = skill_learning.pending_skill_suggestions()

            self.assertEqual(suggestions[0]["skill_name"], "telegram-start-bot")
            self.assertEqual(suggestions[0]["title"], "Criar skill: telegram start bot")

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
                pending = skill_learning.pending_skill_suggestions()

        self.assertIn("Skill procedural aprovada", result)
        self.assertEqual(state["suggestions"][0]["status"], "approved")
        self.assertEqual(pending, [])

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
                pending = skill_learning.pending_skill_suggestions()

        self.assertEqual(result, "Sugestao de skill rejeitada.")
        self.assertEqual(state["suggestions"][0]["status"], "rejected")
        self.assertEqual(pending, [])


if __name__ == "__main__":
    unittest.main()
