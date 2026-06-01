import unittest

from core.multi_agent_handoff import build_handoff_chain, format_handoff_chain, handoff_needed


class MultiAgentHandoffTests(unittest.TestCase):
    def test_builds_chain_for_cross_domain_request(self):
        chain = build_handoff_chain(
            "pesquisar noticia atual e revisar codigo do projeto",
            "respond",
            primary_toolset="programacao",
            primary_agent="dev_agent",
        )

        agents = {item["agent"] for item in chain}
        self.assertIn("dev_agent", agents)
        self.assertIn("research_agent", agents)

    def test_detects_handoff_need_for_complex_chain(self):
        chain = [
            {"agent": "dev_agent", "toolset": "programacao"},
            {"agent": "research_agent", "toolset": "pesquisa"},
        ]

        self.assertTrue(
            handoff_needed(
                "compare codigo com fontes atuais",
                "respond",
                intent_level="pergunta",
                complexity_kind="complex_reasoning",
                chain=chain,
            )
        )

    def test_formats_handoff_chain(self):
        text = format_handoff_chain([
            {"agent": "dev_agent", "toolset": "programacao", "role": "primary"},
            {"agent": "research_agent", "toolset": "pesquisa", "role": "handoff"},
        ])

        self.assertIn("dev_agent via programacao", text)
        self.assertIn("research_agent via pesquisa", text)


if __name__ == "__main__":
    unittest.main()
