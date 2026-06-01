import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.memory_commands import maybe_handle_long_memory_command
from memory import workflow_planner


class WorkflowPlannerTests(unittest.TestCase):
    def _patch_paths(self, temp_dir: str):
        workflow_dir = Path(temp_dir) / "workflows"
        return (
            patch.object(workflow_planner, "WORKFLOW_DIR", workflow_dir),
            patch.object(workflow_planner, "WORKFLOW_INDEX_PATH", workflow_dir / "index.json"),
        )

    def test_create_workflow_plan_writes_markdown_and_index(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self._patch_paths(temp_dir)[0], self._patch_paths(temp_dir)[1]:
                plan = workflow_planner.create_workflow_plan("melhorar o HUD")

                path = Path(plan["path"])
                self.assertTrue(path.exists())
                self.assertIn("## Ideia", path.read_text(encoding="utf-8"))
                self.assertEqual(workflow_planner.list_workflow_plans()[0]["title"], "melhorar o HUD")

    def test_update_step_advances_current_step(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self._patch_paths(temp_dir)[0], self._patch_paths(temp_dir)[1]:
                workflow_planner.create_workflow_plan("integrar agenda")

                updated = workflow_planner.update_workflow_step(1)

                self.assertEqual(updated["completed_steps"], 1)
                self.assertIn("Levantar contexto", updated["current_step"])

    def test_memory_commands_create_show_and_list_workflow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self._patch_paths(temp_dir)[0], self._patch_paths(temp_dir)[1]:
                created = maybe_handle_long_memory_command("criar plano duravel para estudar python")
                current = maybe_handle_long_memory_command("workflow atual")
                listed = maybe_handle_long_memory_command("listar planos duraveis")

                self.assertIn("Workflow duravel criado", created)
                self.assertIn("estudar python", current)
                self.assertIn("Workflows duraveis", listed)

    def test_memory_commands_update_and_close_workflow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self._patch_paths(temp_dir)[0], self._patch_paths(temp_dir)[1]:
                maybe_handle_long_memory_command("criar workflow para revisar carteira")

                updated = maybe_handle_long_memory_command("concluir etapa 1 do workflow")
                closed = maybe_handle_long_memory_command("fechar workflow duravel com entregue")

                self.assertIn("Etapa atualizada", updated)
                self.assertIn("Workflow duravel fechado", closed)


if __name__ == "__main__":
    unittest.main()
