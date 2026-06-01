import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import operational_context, task_evaluation


class TaskEvaluationTests(unittest.TestCase):
    def test_record_and_update_latest_task_evaluation(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task_evaluations.json"

            recorded = task_evaluation.record_task_evaluation(
                action="respond",
                success=True,
                result="ok",
                path=path,
            )
            updated = task_evaluation.update_latest_task_evaluation(
                "precisa de ajuste",
                note="resposta curta demais",
                path=path,
            )

        self.assertEqual(recorded["status"], "success")
        self.assertEqual(updated["status"], "needs_adjustment")
        self.assertIn("curta demais", updated["note"])

    def test_summary_counts_and_ranks_sensitive_actions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task_evaluations.json"

            task_evaluation.record_task_evaluation(action="open_app", success=True, path=path)
            task_evaluation.record_task_evaluation(action="open_app", status="nao funcionou", path=path)
            task_evaluation.record_task_evaluation(action="screen_analyze", status="precisa ajuste", path=path)

            summary = task_evaluation.task_evaluation_summary(path=path)

        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["counts"]["success"], 1)
        self.assertEqual(summary["counts"]["failure"], 1)
        self.assertEqual(summary["counts"]["needs_adjustment"], 1)
        self.assertEqual(summary["by_action"][0]["action"], "open_app")

    def test_format_empty_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "task_evaluations.json"
            with patch.object(task_evaluation, "TASK_EVALUATIONS_PATH", path):
                text = task_evaluation.format_task_evaluation_summary()

        self.assertIn("Ainda nao ha autoavaliacoes", text)

    def test_operational_context_includes_task_evaluation_overview(self):
        with patch("memory.task_evaluation.task_evaluation_summary", return_value={
            "total": 2,
            "counts": {"success": 1, "failure": 1, "needs_adjustment": 0},
            "success_rate": 0.5,
            "by_action": [{"action": "respond", "failure": 1, "needs_adjustment": 0, "total": 2}],
            "recent": [{"action": "respond", "status": "failure"}],
        }):
            overview = operational_context._load_task_evaluation_overview()

        self.assertEqual(overview["total"], 2)
        self.assertEqual(overview["counts"]["failure"], 1)

    def test_operational_context_includes_capability_ranking_overview(self):
        with patch("memory.capability_ranking.capability_rankings", return_value={
            "agent": [{"name": "research_agent", "utility": 3.0}],
            "toolset": [{"name": "pesquisa", "utility": 3.0}],
            "skill": [{"name": "pesquisa-web", "utility": 3.0}],
        }):
            overview = operational_context._load_capability_ranking_overview()

        self.assertEqual(overview["agents"][0]["name"], "research_agent")
        self.assertEqual(overview["toolsets"][0]["name"], "pesquisa")


if __name__ == "__main__":
    unittest.main()
