import unittest

from core.router_memory import detect_action_core_command, detect_memory_command


class RouterMemoryTests(unittest.TestCase):
    def test_detects_memory_remember(self):
        result = detect_memory_command("lembre na memoria que briefing deve ser curto")

        self.assertEqual(result["intent"], "action_memory_remember")
        self.assertEqual(
            result["target"],
            {
                "namespace": "investments",
                "key": "briefing_deve_ser_curto",
                "value": "briefing deve ser curto",
            },
        )

    def test_detects_preference_memory(self):
        result = detect_memory_command("lembre que eu prefiro respostas curtas")

        self.assertEqual(result["intent"], "action_memory_remember")
        self.assertEqual(result["target"]["namespace"], "preferences")
        self.assertEqual(result["target"]["key"], "respostas_curtas")

    def test_detects_project_idea_memory_with_axel_prefix(self):
        result = detect_memory_command('axel guarde a ideia de projeto "criar um aplicativo de devocional"')

        self.assertEqual(result["intent"], "action_memory_remember")
        self.assertEqual(result["target"]["namespace"], "projects")
        self.assertEqual(result["target"]["key"], "ideia_projeto_criar_aplicativo_devocional")
        self.assertEqual(result["target"]["value"], "ideia de projeto: criar um aplicativo de devocional")

    def test_detects_memory_recall(self):
        result = detect_memory_command("o que voce sabe sobre briefing deve ser curto")

        self.assertEqual(result["intent"], "action_memory_recall")
        self.assertEqual(result["target"], {"namespace": "investments", "key": "briefing_deve_ser_curto"})

    def test_detects_memory_list_namespace(self):
        result = detect_memory_command("listar memoria investimentos")

        self.assertEqual(result, {"intent": "action_memory_list", "target": "investments"})

    def test_detects_action_tool_execute_with_json_arguments(self):
        result = detect_action_core_command('executar action file.process {"path":"README.md","max_chars":1000}')

        self.assertEqual(result["intent"], "action_tool_execute")
        self.assertEqual(result["target"], {"name": "file.process", "arguments": {"path": "README.md", "max_chars": 1000}})

    def test_detects_action_tool_list_by_category(self):
        result = detect_action_core_command("listar actions memoria")

        self.assertEqual(result, {"intent": "action_tool_list", "target": "memory"})

    def test_detects_memory_backup_shortcuts(self):
        self.assertEqual(
            detect_action_core_command("backup da memoria"),
            {"intent": "action_tool_execute", "target": {"name": "memory.backup.create", "arguments": {}}},
        )
        self.assertEqual(
            detect_action_core_command("backups da memoria"),
            {"intent": "action_tool_execute", "target": {"name": "memory.backup.list", "arguments": {}}},
        )


if __name__ == "__main__":
    unittest.main()
