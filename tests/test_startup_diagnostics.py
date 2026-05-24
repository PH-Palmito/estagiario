import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core import startup_diagnostics


class StartupDiagnosticsTests(unittest.TestCase):
    def test_startup_diagnostics_enabled_only_for_startup_flag(self):
        self.assertTrue(startup_diagnostics.startup_diagnostics_enabled(["main.py", "--startup"]))
        self.assertFalse(startup_diagnostics.startup_diagnostics_enabled(["main.py", "--voice"]))

    def test_startup_log_path_uses_tmp_log_under_repo_root(self):
        root = Path("C:/project")

        result = startup_diagnostics.startup_log_path(root)

        self.assertEqual(result, root / ".tmp" / "axel-startup.log")

    def test_append_startup_log_creates_parent_and_appends_message(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "nested" / "startup.log"

            startup_diagnostics.append_startup_log("primeira linha", log_path)
            startup_diagnostics.append_startup_log("segunda linha", log_path)

            content = log_path.read_text(encoding="utf-8")

        self.assertIn("primeira linha", content)
        self.assertIn("segunda linha", content)
        self.assertGreaterEqual(content.count("\n"), 2)

    def test_run_without_startup_diagnostics_only_calls_main(self):
        calls = []

        startup_diagnostics.run_with_startup_diagnostics(["main.py"], lambda: calls.append("main"))

        self.assertEqual(calls, ["main"])

    def test_run_with_startup_diagnostics_logs_start_and_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "startup.log"
            with patch.object(startup_diagnostics, "startup_log_path", return_value=log_path):
                startup_diagnostics.run_with_startup_diagnostics(["main.py", "--startup"], lambda: None)

            content = log_path.read_text(encoding="utf-8")

        self.assertIn("Bootstrap do Axel iniciado.", content)
        self.assertIn("Bootstrap do Axel encerrado.", content)

    def test_run_with_startup_diagnostics_logs_traceback_and_reraises(self):
        def boom():
            raise RuntimeError("falha controlada")

        with tempfile.TemporaryDirectory() as tmp:
            log_path = Path(tmp) / "startup.log"
            with patch.object(startup_diagnostics, "startup_log_path", return_value=log_path):
                with self.assertRaises(RuntimeError):
                    startup_diagnostics.run_with_startup_diagnostics(["main.py", "--startup"], boom)

            content = log_path.read_text(encoding="utf-8")

        self.assertIn("Falha fatal durante o startup", content)
        self.assertIn("RuntimeError: falha controlada", content)


if __name__ == "__main__":
    unittest.main()
