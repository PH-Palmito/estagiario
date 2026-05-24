import tempfile
import unittest
from pathlib import Path

from core.project_health import (
    build_project_health_snapshot,
    format_project_health_panel,
    memory_artifact_summary,
    project_change_summary,
    recent_execution_summary,
    run_estagiario_preflight,
    validate_project_jsons,
)


class ProjectHealthTests(unittest.TestCase):
    def test_validate_project_jsons_reports_invalid_memory_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "routines.json").write_text('{"ok": true}', encoding="utf-8")
            (memory / "ui_state.json").write_text("{invalid", encoding="utf-8")

            ok, errors = validate_project_jsons(root)

            self.assertEqual(ok, ["memory/routines.json"])
            self.assertEqual(len(errors), 1)
            self.assertIn("memory/ui_state.json", errors[0])

    def test_project_change_summary_handles_non_git_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = project_change_summary(Path(temp_dir))

            self.assertEqual(summary, "sem repositorio git local detectado")

    def test_run_estagiario_preflight_returns_stable_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_estagiario_preflight(Path(temp_dir))

            self.assertIn("compiled_modules", result)
            self.assertIn("compile_error", result)
            self.assertIn("json_ok_count", result)
            self.assertIn("json_errors", result)
            self.assertIn("change_summary", result)

    def test_memory_artifact_summary_counts_runtime_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "ui_state.json").write_text("{}", encoding="utf-8")
            (memory / "handoff.tmp").write_text("tmp", encoding="utf-8")
            (memory / "page.html").write_text("<html></html>", encoding="utf-8")
            (memory / "visible.txt").write_text("texto", encoding="utf-8")

            result = memory_artifact_summary(root)

            self.assertEqual(result["json"], 1)
            self.assertEqual(result["tmp"], 1)
            self.assertEqual(result["html"], 1)
            self.assertEqual(result["txt"], 1)

    def test_recent_execution_summary_reports_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "execution_log.jsonl").write_text(
                '{"event":"assistant_output","data":{"message":"ok"}}\n'
                '{"event":"tool_error","data":{"message":"Erro ao abrir"}}\n',
                encoding="utf-8",
            )

            result = recent_execution_summary(root)

            self.assertEqual(result["events_count"], 2)
            self.assertEqual(result["recent_errors"], ["Erro ao abrir"])

    def test_format_project_health_panel_summarizes_snapshot(self):
        snapshot = {
            "status": "saudavel",
            "preflight": {
                "compiled_modules": ["main.py"],
                "compile_error": "",
                "json_ok_count": 2,
                "json_errors": [],
                "change_summary": "limpo",
            },
            "execution": {"events_count": 3, "recent_errors": []},
            "actions": {"count": 10, "categories": {}, "error": ""},
            "artifacts": {"json": 4, "tmp": 1, "html": 2, "txt": 3},
        }

        result = format_project_health_panel(snapshot)

        self.assertIn("Saude do Axel: projeto saudavel.", result)
        self.assertIn("Compilacao ok em 1 modulos-chave.", result)
        self.assertIn("Actions registradas: 10.", result)

    def test_build_project_health_snapshot_has_panel_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "memory").mkdir()

            result = build_project_health_snapshot(root)

            self.assertIn("status", result)
            self.assertIn("preflight", result)
            self.assertIn("execution", result)
            self.assertIn("artifacts", result)
            self.assertIn("actions", result)


if __name__ == "__main__":
    unittest.main()
