import unittest

from core.decision_orchestrator import build_decision_plan
from core.router_registry import INTENT_LEVEL_DIRECT_COMMAND, INTENT_LEVEL_QUESTION


class DecisionOrchestratorTests(unittest.TestCase):
    def test_selects_programming_toolset_for_code_request(self):
        plan = build_decision_plan(
            "revisar codigo e rodar testes",
            {"intent": "respond"},
            intent_level=INTENT_LEVEL_QUESTION,
            complexity_kind="complex_reasoning",
        )

        self.assertEqual(plan.toolset, "programacao")
        self.assertEqual(plan.agent, "dev_agent")
        self.assertEqual(plan.response_mode, "answer_with_context")
        self.assertFalse(plan.needs_confirmation)
        self.assertEqual(plan.coordination_mode, "single_agent")
        self.assertEqual(plan.tool_libraries[0]["agent"], "dev_agent")

    def test_marks_critical_file_intent_for_confirmation(self):
        plan = build_decision_plan(
            "apague esse arquivo",
            {"intent": "file_delete"},
            intent_level=INTENT_LEVEL_DIRECT_COMMAND,
            complexity_kind="simple_command",
        )

        self.assertEqual(plan.risk_level, "critical")
        self.assertTrue(plan.needs_confirmation)
        self.assertEqual(plan.response_mode, "confirm_then_act")

    def test_falls_back_to_system_for_direct_command(self):
        plan = build_decision_plan(
            "abrir calculadora",
            {"intent": "open_app"},
            intent_level=INTENT_LEVEL_DIRECT_COMMAND,
            complexity_kind="simple_command",
        )

        self.assertEqual(plan.toolset, "sistema")
        self.assertEqual(plan.agent, "system_agent")
        self.assertEqual(plan.model_policy, "local_first")

    def test_builds_multi_agent_handoff_for_cross_domain_task(self):
        plan = build_decision_plan(
            "pesquisar noticia atual com fontes e revisar codigo do projeto",
            {"intent": "respond"},
            intent_level=INTENT_LEVEL_QUESTION,
            complexity_kind="complex_reasoning",
        )

        agents = {item["agent"] for item in plan.handoff_chain}
        self.assertEqual(plan.coordination_mode, "multi_agent_handoff")
        self.assertIn("research_agent", agents)
        self.assertIn("dev_agent", agents)
        library_agents = {item["agent"] for item in plan.tool_libraries}
        self.assertIn("research_agent", library_agents)
        self.assertIn("dev_agent", library_agents)


if __name__ == "__main__":
    unittest.main()
