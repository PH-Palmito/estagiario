import unittest

from core.specialist_agents import format_agent_catalog, format_relevant_agents, list_agents, select_agents


class SpecialistAgentsTests(unittest.TestCase):
    def test_list_agents_contains_expected_domains(self):
        names = {item["name"] for item in list_agents()}

        self.assertIn("dev_agent", names)
        self.assertIn("research_agent", names)
        self.assertIn("investment_agent", names)
        self.assertIn("browser_agent", names)
        self.assertIn("system_agent", names)
        self.assertIn("memory_agent", names)
        self.assertIn("voice_agent", names)

    def test_select_agents_uses_query_and_toolset(self):
        matches = select_agents("resumo de dividendos da carteira", toolset="carteira")

        self.assertEqual(matches[0]["name"], "investment_agent")

    def test_formats_catalog_and_relevant_agents(self):
        self.assertIn("Agentes especialistas do Axel", format_agent_catalog())
        self.assertIn("Agente de Programacao", format_relevant_agents("bug no codigo"))


if __name__ == "__main__":
    unittest.main()
