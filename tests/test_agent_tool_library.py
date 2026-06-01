import unittest

from core.agent_tool_library import categories_for_agent, format_agent_tool_library, tool_library_for_agent, tool_library_for_chain


class AgentToolLibraryTests(unittest.TestCase):
    def test_maps_agent_to_relevant_categories(self):
        self.assertIn("code", categories_for_agent("dev_agent"))
        self.assertIn("browser", categories_for_agent("browser_agent"))
        self.assertIn("investments", categories_for_agent("investment_agent"))

    def test_filters_actions_by_agent_categories(self):
        library = tool_library_for_agent("dev_agent", limit=80)
        categories = {item["category"] for item in library["actions"]}

        self.assertIn("code", categories)
        self.assertNotIn("investments", categories)

    def test_builds_library_for_handoff_chain_without_duplicates(self):
        libraries = tool_library_for_chain([
            {"agent": "dev_agent"},
            {"agent": "research_agent"},
            {"agent": "dev_agent"},
        ])

        self.assertEqual([item["agent"] for item in libraries], ["dev_agent", "research_agent"])

    def test_formats_agent_tool_library(self):
        text = format_agent_tool_library("system_agent")

        self.assertIn("Biblioteca de ferramentas de system_agent", text)
        self.assertIn("categorias", text)


if __name__ == "__main__":
    unittest.main()
