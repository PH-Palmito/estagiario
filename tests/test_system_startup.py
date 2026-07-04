import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.system_tools import (
    enable_windows_startup,
    install_windows_app_shortcuts,
    uninstall_windows_app_shortcuts,
    windows_app_status,
    windows_startup_diagnostics,
    windows_startup_status,
)


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
            briefing_state_path = Path(tmpdir) / "startup_briefing_state.json"
            briefing_state_path.write_text(
                '{"last_briefing_date":"2026-06-08","last_briefing_at":"2026-06-08T07:55:14"}',
                encoding="utf-8",
            )
            with (
                patch.dict(os.environ, {"APPDATA": tmpdir}),
                patch("tools.system_tools.startup_log_path", return_value=log_path),
                patch("tools.system_tools._startup_briefing_state_path", return_value=briefing_state_path),
            ):
                enable_windows_startup()
                result = windows_startup_status()

        self.assertIn("esta ativada", result)
        self.assertIn("atalho esta atualizado", result)
        self.assertIn("axel-startup.log", result)
        self.assertIn("briefing marcado em 2026-06-08T07:55:14", result)

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

    def test_install_windows_app_shortcuts_creates_start_menu_and_desktop_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            user = Path(tmpdir) / "user"
            appdata = user / "AppData" / "Roaming"
            desktop = user / "Desktop"
            desktop.mkdir(parents=True)

            def fake_shortcut(path, **_kwargs):
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_text("shortcut", encoding="utf-8")

            with (
                patch.dict(os.environ, {"APPDATA": str(appdata), "USERPROFILE": str(user)}),
                patch("tools.system_tools._create_windows_shortcut", side_effect=fake_shortcut),
            ):
                result = install_windows_app_shortcuts()
                status = windows_app_status()
                start_exists = (appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Axel" / "Axel.lnk").exists()
                desktop_exists = (desktop / "Axel.lnk").exists()

        self.assertIn("App do Axel instalado", result)
        self.assertIn("App do Axel: instalado", status)
        self.assertTrue(start_exists)
        self.assertTrue(desktop_exists)

    def test_uninstall_windows_app_shortcuts_removes_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            user = Path(tmpdir) / "user"
            appdata = user / "AppData" / "Roaming"
            desktop = user / "Desktop"
            start_shortcut = appdata / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Axel" / "Axel.lnk"
            desktop_shortcut = desktop / "Axel.lnk"
            start_shortcut.parent.mkdir(parents=True)
            desktop_shortcut.parent.mkdir(parents=True)
            start_shortcut.write_text("shortcut", encoding="utf-8")
            desktop_shortcut.write_text("shortcut", encoding="utf-8")

            with patch.dict(os.environ, {"APPDATA": str(appdata), "USERPROFILE": str(user)}):
                result = uninstall_windows_app_shortcuts()

        self.assertIn("removidos", result)
        self.assertFalse(start_shortcut.exists())
        self.assertFalse(desktop_shortcut.exists())

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
