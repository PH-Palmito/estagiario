import unittest

from actions.registry import ActionSpec, execute_action_result, register_action
from core.action_errors import format_action_failure_message, infer_error_category
from core.command_schema import Command
from core.executor import execute_result


class ActionErrorTests(unittest.TestCase):
    def test_infers_error_category_from_action_name(self):
        self.assertEqual(infer_error_category("browser_find"), "browser")
        self.assertEqual(infer_error_category("file_read"), "files")
        self.assertEqual(infer_error_category("image_analyze_screen"), "vision")
        self.assertEqual(infer_error_category("weather_summary"), "network")

    def test_formats_browser_error_with_recovery_hint(self):
        message = format_action_failure_message("browser_find", "browser", "window not found")

        self.assertIn("Nao consegui concluir a acao no navegador.", message)
        self.assertIn("Edge/Chrome", message)
        self.assertIn("window not found", message)

    def test_registry_standardizes_registered_action_exception(self):
        def fail(_args):
            raise RuntimeError("sem permissao")

        register_action(
            ActionSpec(
                name="unit.file_boom",
                description="Falha de arquivo.",
                handler=fail,
                category="files",
            )
        )

        result = execute_action_result("unit.file_boom", {})

        self.assertFalse(result.success)
        self.assertIn("Nao consegui acessar o arquivo ou pasta.", result.message)
        self.assertIn("Confira o caminho", result.message)
        self.assertEqual(result.error, "sem permissao")
        self.assertEqual(result.data["category"], "files")

    def test_executor_standardizes_registered_action_exception(self):
        def fail(_args):
            raise RuntimeError("modelo visual indisponivel")

        register_action(
            ActionSpec(
                name="unit.vision_boom",
                description="Falha visual.",
                handler=fail,
                category="vision",
            )
        )

        result = execute_result(Command(action="unit.vision_boom", params={}))

        self.assertFalse(result.success)
        self.assertIn("Nao consegui concluir a leitura visual.", result.message)
        self.assertIn("modelo visual indisponivel", result.message)


if __name__ == "__main__":
    unittest.main()
