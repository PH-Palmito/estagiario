import unittest
from unittest.mock import patch

from core.agent_operations import format_agent_operations_detail, format_agent_operations_overview
from core.specialist_agents import find_agent


class AgentOperationsTests(unittest.TestCase):
    def test_find_agent_by_name_toolset_and_title(self):
        self.assertEqual(find_agent("dev_agent")["name"], "dev_agent")
        self.assertEqual(find_agent("programacao")["name"], "dev_agent")
        self.assertEqual(find_agent("Agente de Pesquisa")["name"], "research_agent")
        self.assertEqual(find_agent("estudos")["name"], "study_agent")

    @patch("core.agent_operations.capability_rankings")
    @patch("core.agent_operations.tool_library_for_agent")
    def test_agent_detail_includes_mission_tools_and_metrics(self, library, rankings):
        library.return_value = {
            "categories": ["code", "files"],
            "actions": [
                {"name": "file.read", "read_only": True},
                {"name": "file.write", "read_only": False},
            ],
        }
        rankings.return_value = {
            "agent": [
                {
                    "name": "dev_agent",
                    "total": 3,
                    "success": 2,
                    "failure": 1,
                    "needs_adjustment": 0,
                    "utility": 4.2,
                    "recent_actions": ["file.read"],
                }
            ]
        }

        result = format_agent_operations_detail("dev_agent")

        self.assertIn("Agente de Programação", result)
        self.assertIn("Actions úteis", result)
        self.assertIn("file.read", result)
        self.assertIn("uso 3", result)
        self.assertIn("Ações recentes: file.read", result)

    @patch("core.agent_operations.capability_rankings", return_value={"agent": []})
    def test_agent_overview_lists_operational_agents(self, _rankings):
        result = format_agent_operations_overview()

        self.assertIn("Agentes operacionais do Axel", result)
        self.assertIn("dev_agent", result)
        self.assertIn("study_agent", result)
        self.assertIn("voice_agent", result)


if __name__ == "__main__":
    unittest.main()
