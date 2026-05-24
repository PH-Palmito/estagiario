import unittest

from core.router_system import detect_run_script, detect_type_text, detect_windows_startup_command


class RouterSystemTests(unittest.TestCase):
    def test_windows_startup_enable(self):
        self.assertEqual(
            detect_windows_startup_command("fazer o Axel iniciar junto com o Windows"),
            {"intent": "windows_startup_enable", "target": None},
        )

    def test_windows_startup_disable(self):
        self.assertEqual(
            detect_windows_startup_command("desativar iniciar junto com o Windows"),
            {"intent": "windows_startup_disable", "target": None},
        )

    def test_windows_startup_status(self):
        self.assertEqual(
            detect_windows_startup_command("status iniciar junto com o Windows"),
            {"intent": "windows_startup_status", "target": None},
        )

    def test_run_script(self):
        self.assertEqual(
            detect_run_script("execute script scripts/teste.py"),
            {"intent": "run_script", "target": "scripts/teste.py"},
        )

    def test_type_text(self):
        self.assertEqual(
            detect_type_text("digite olá mundo"),
            {"intent": "type_text", "target": None, "content": "olá mundo"},
        )

    def test_type_text_without_content(self):
        self.assertIsNone(detect_type_text("digite"))


if __name__ == "__main__":
    unittest.main()
