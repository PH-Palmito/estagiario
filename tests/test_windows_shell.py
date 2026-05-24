import unittest
from types import SimpleNamespace

from tools.windows_shell import (
    activate_window_names,
    get_clipboard_text,
    run_powershell,
    set_clipboard_text,
)


class WindowsShellTests(unittest.TestCase):
    def test_run_powershell_builds_encoded_command(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(stdout="ok", returncode=0)

        result = run_powershell("Write-Output 'ok'", timeout_seconds=7, powershell_exe="pwsh", subprocess_run=fake_run)

        self.assertEqual(result.stdout, "ok")
        self.assertEqual(calls[0][0][0], "pwsh")
        self.assertIn("-EncodedCommand", calls[0][0])
        self.assertEqual(calls[0][1]["timeout"], 7)
        self.assertEqual(calls[0][1]["encoding"], "utf-8")

    def test_get_clipboard_text_returns_stdout_or_empty_on_error(self):
        def fake_run(script, timeout_seconds=10):
            self.assertIn("Get-Clipboard", script)
            self.assertEqual(timeout_seconds, 3)
            return SimpleNamespace(stdout="texto", returncode=0)

        self.assertEqual(get_clipboard_text(run_powershell_func=fake_run), "texto")

        def failing_run(*args, **kwargs):
            raise RuntimeError("boom")

        self.assertEqual(get_clipboard_text(run_powershell_func=failing_run), "")

    def test_set_clipboard_text_uses_stdin(self):
        calls = []

        def fake_run(args, **kwargs):
            calls.append((args, kwargs))
            return SimpleNamespace(stdout="", returncode=0)

        set_clipboard_text("abc", powershell_exe="pwsh", subprocess_run=fake_run)

        self.assertEqual(calls[0][0][0], "pwsh")
        self.assertEqual(calls[0][1]["input"], "abc")
        self.assertEqual(calls[0][1]["timeout"], 3)

    def test_activate_window_names_filters_empty_names_and_checks_output(self):
        calls = []

        def fake_run(script, timeout_seconds=10):
            calls.append(script)
            return SimpleNamespace(stdout="OK", returncode=0)

        self.assertTrue(activate_window_names(["", "Chrome"], run_powershell_func=fake_run))
        self.assertIn("'Chrome'", calls[0])

        def no_run(script, timeout_seconds=10):
            return SimpleNamespace(stdout="NO", returncode=0)

        self.assertFalse(activate_window_names(["Chrome"], run_powershell_func=no_run))
        self.assertFalse(activate_window_names([], run_powershell_func=fake_run))


if __name__ == "__main__":
    unittest.main()
