import unittest
from types import SimpleNamespace

from tools.windows_window import (
    app_window_rect,
    first_window_rect,
    foreground_window_capture_hash,
)


class WindowsWindowTests(unittest.TestCase):
    def test_app_window_rect_parses_valid_rect(self):
        calls = []

        def fake_run(script, timeout_seconds=10):
            calls.append(script)
            return SimpleNamespace(stdout="__RECT__:1,2,101,202", returncode=0)

        self.assertEqual(app_window_rect("chrome", run_powershell_func=fake_run), (1, 2, 101, 202))
        self.assertIn('Get-Process -Name "chrome"', calls[0])

    def test_app_window_rect_rejects_missing_or_invalid_rect(self):
        def no_rect(script, timeout_seconds=10):
            return SimpleNamespace(stdout="__NO_RECT__", returncode=0)

        self.assertIsNone(app_window_rect("chrome", run_powershell_func=no_rect))

        def invalid_rect(script, timeout_seconds=10):
            return SimpleNamespace(stdout="__RECT__:1,2,1,2", returncode=0)

        self.assertIsNone(app_window_rect("chrome", run_powershell_func=invalid_rect))

    def test_first_window_rect_returns_first_available_rect(self):
        def get_rect(name):
            if name == "msedge":
                return (1, 2, 3, 4)
            return None

        self.assertEqual(first_window_rect(["chrome", "msedge"], get_app_window_rect_func=get_rect), (1, 2, 3, 4))
        self.assertIsNone(first_window_rect(["chrome"], get_app_window_rect_func=get_rect))

    def test_foreground_window_capture_hash_runs_script_and_cleans_file(self):
        removed = []
        scripts = []

        def fake_run(script, timeout_seconds=10):
            scripts.append((script, timeout_seconds))
            return SimpleNamespace(stdout="ABCDEF", returncode=0)

        result = foreground_window_capture_hash(
            get_rect_func=lambda: (0, 0, 120, 100),
            run_powershell_func=fake_run,
            getcwd=lambda: "C:\\tmp",
            makedirs=lambda *args, **kwargs: None,
            path_exists=lambda path: True,
            remove=lambda path: removed.append(path),
            monotonic_ns=lambda: 123,
        )

        self.assertEqual(result, "abcdef")
        self.assertEqual(scripts[0][1], 5)
        self.assertTrue(removed[0].endswith("screen-context-123.png"))

    def test_foreground_window_capture_hash_handles_small_rect_and_errors(self):
        self.assertEqual(
            foreground_window_capture_hash(get_rect_func=lambda: (0, 0, 20, 20), run_powershell_func=lambda *a, **k: None),
            "",
        )

        removed = []

        def failing_run(*args, **kwargs):
            raise RuntimeError("boom")

        result = foreground_window_capture_hash(
            get_rect_func=lambda: (0, 0, 120, 100),
            run_powershell_func=failing_run,
            getcwd=lambda: "C:\\tmp",
            makedirs=lambda *args, **kwargs: None,
            path_exists=lambda path: True,
            remove=lambda path: removed.append(path),
            monotonic_ns=lambda: 456,
        )

        self.assertEqual(result, "")
        self.assertTrue(removed)


if __name__ == "__main__":
    unittest.main()
