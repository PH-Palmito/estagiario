import unittest

from core.router_code import detect_code_inspection_command


class RouterCodeTests(unittest.TestCase):
    def test_detects_workspace_inspection(self):
        self.assertEqual(
            detect_code_inspection_command("analise o codigo"),
            {"intent": "code_inspect_workspace", "target": None},
        )

    def test_detects_selection_inspection(self):
        self.assertEqual(
            detect_code_inspection_command("inspecionar codigo selecionado"),
            {"intent": "code_inspect_selection", "target": None},
        )

    def test_detects_target_inspection(self):
        self.assertEqual(
            detect_code_inspection_command("analise o arquivo main.py"),
            {"intent": "code_inspect_target", "target": "main.py"},
        )


if __name__ == "__main__":
    unittest.main()
