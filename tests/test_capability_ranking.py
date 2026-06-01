import tempfile
import unittest
from pathlib import Path

from memory.capability_ranking import capability_rankings, format_capability_rankings
from memory.task_evaluation import record_task_evaluation


class CapabilityRankingTests(unittest.TestCase):
    def test_ranks_agents_toolsets_skills_and_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task_evaluations.json"
            record_task_evaluation(
                action="respond",
                success=True,
                metadata={"agent": "research_agent", "toolset": "pesquisa", "skills": ["pesquisa-web"]},
                path=path,
            )
            record_task_evaluation(
                action="respond",
                success=True,
                metadata={"agent": "research_agent", "toolset": "pesquisa", "skills": ["pesquisa-web"]},
                path=path,
            )
            record_task_evaluation(
                action="open_app",
                success=False,
                metadata={"agent": "system_agent", "toolset": "sistema", "skills": ["apps"]},
                path=path,
            )

            rankings = capability_rankings(path=path)

        self.assertEqual(rankings["agent"][0]["name"], "research_agent")
        self.assertEqual(rankings["toolset"][0]["name"], "pesquisa")
        self.assertEqual(rankings["skill"][0]["name"], "pesquisa-web")
        self.assertEqual(rankings["action"][0]["name"], "respond")
        self.assertEqual(rankings["agent"][0]["success"], 2)

    def test_formats_empty_ranking(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task_evaluations.json"
            from memory import capability_ranking

            original = capability_ranking.capability_rankings
            try:
                capability_ranking.capability_rankings = lambda limit=5: original(limit=limit, path=path)
                text = format_capability_rankings("agent")
            finally:
                capability_ranking.capability_rankings = original

        self.assertIn("Ranking de agentes", text)
        self.assertIn("sem dados", text)


if __name__ == "__main__":
    unittest.main()
