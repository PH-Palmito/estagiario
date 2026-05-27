import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.system_tools import enable_windows_startup, windows_startup_diagnostics, windows_startup_status


class SystemStartupTests(unittest.TestCase):
    def test_enable_windows_startup_writes_logged_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / ".tmp" / "axel-startup.log"
            with patch.dict(os.environ, {"APPDATA": tmpdir}), patch("tools.system_tools.startup_log_path", return_value=log_path):
                result = enable_windows_startup()
                entry = self._startup_entry(tmpdir)
                content = entry.read_text(encoding="utf-8")

        self.assertIn("Inicializacao com o Windows ativada.", result)
        self.assertIn("axel-startup.log", result)
        self.assertIn("Iniciando Axel pelo Windows Startup", content)
        self.assertIn("axel-startup-output.log", content)
        self.assertIn(">>", content)
        self.assertIn("2>&1", content)
        self.assertIn("--startup", content)

    def test_windows_startup_status_reports_current_entry_and_log_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / ".tmp" / "axel-startup.log"
            with patch.dict(os.environ, {"APPDATA": tmpdir}), patch("tools.system_tools.startup_log_path", return_value=log_path):
                enable_windows_startup()
                result = windows_startup_status()

        self.assertIn("esta ativada", result)
        self.assertIn("atalho esta atualizado", result)
        self.assertIn("axel-startup.log", result)

    def test_windows_startup_status_reports_outdated_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / ".tmp" / "axel-startup.log"
            with patch.dict(os.environ, {"APPDATA": tmpdir}), patch("tools.system_tools.startup_log_path", return_value=log_path):
                entry = self._startup_entry(tmpdir)
                entry.parent.mkdir(parents=True, exist_ok=True)
                entry.write_text("@echo off\n", encoding="utf-8")

                result = windows_startup_status()

        self.assertIn("Alerta", result)
        self.assertIn("atalho esta desatualizado", result)
        self.assertIn("--install-startup", result)
        self.assertIn("content_mismatch", result)

    def test_windows_startup_diagnostics_reports_logs_and_current_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = Path(tmpdir) / ".tmp" / "axel-startup.log"
            with patch.dict(os.environ, {"APPDATA": tmpdir}), patch("tools.system_tools.startup_log_path", return_value=log_path):
                enable_windows_startup()
                diagnostics = windows_startup_diagnostics()

        self.assertTrue(diagnostics["available"])
        self.assertTrue(diagnostics["enabled"])
        self.assertTrue(diagnostics["current"])
        self.assertFalse(diagnostics["outdated"])
        self.assertIn("--startup", diagnostics["expected_command"])
        self.assertIn("axel-startup.log", diagnostics["log_path"])

    def _startup_entry(self, appdata: str) -> Path:
        return (
            Path(appdata)
            / "Microsoft"
            / "Windows"
            / "Start Menu"
            / "Programs"
            / "Startup"
            / "Axel Assistant.cmd"
        )


if __name__ == "__main__":
    unittest.main()
