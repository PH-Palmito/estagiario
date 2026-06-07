import tempfile
import unittest
from pathlib import Path

from memory.workspace_context import format_workspace_context, load_workspace_context


class WorkspaceContextTests(unittest.TestCase):
    def test_load_workspace_context_finds_agents_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "AGENTS.md").write_text(
                "# Projeto Teste\n\n- Rode testes focados antes de finalizar.\n- Preserve mudancas do usuario.\n",
                encoding="utf-8",
            )

            result = load_workspace_context(root)

        self.assertTrue(result["available"])
        self.assertEqual(result["files"], ["AGENTS.md"])
        self.assertIn("Projeto Teste", result["summary"])
        self.assertIn("Rode testes focados", result["instructions"][0])

    def test_format_workspace_context_when_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = format_workspace_context(Path(temp_dir))

        self.assertIn("Nenhum contexto de workspace encontrado", result)

    def test_load_workspace_context_limits_raw_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".axel").mkdir()
            (root / ".axel" / "context.md").write_text("# Axel\n\n- " + "x" * 7000, encoding="utf-8")

            result = load_workspace_context(root)

        self.assertTrue(result["available"])
        self.assertLessEqual(len(result["contexts"][0]["raw_text"]), 6000)


if __name__ == "__main__":
    unittest.main()
