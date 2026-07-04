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

    def test_reminder_add_is_low_risk_without_confirmation(self):
        plan = build_decision_plan(
            "me lembre todo dia 2 de junho do presente do dia dos namorados dia 12/06",
            {"intent": "reminder_add"},
            intent_level=INTENT_LEVEL_DIRECT_COMMAND,
            complexity_kind="simple_command",
        )

        self.assertEqual(plan.risk_level, "low")
        self.assertFalse(plan.needs_confirmation)
        self.assertEqual(plan.response_mode, "execute_short")

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

    def test_selects_study_agent_for_study_file_task(self):
        plan = build_decision_plan(
            "analisar um PDF de estudo e gerar questões",
            {"intent": "respond"},
            intent_level=INTENT_LEVEL_QUESTION,
            complexity_kind="complex_reasoning",
        )

        self.assertEqual(plan.toolset, "estudos")
        self.assertEqual(plan.agent, "study_agent")

    def test_procedural_skill_trigger_routes_telegram_to_system(self):
        plan = build_decision_plan(
            "iniciar bot telegram",
            {"intent": "respond"},
            intent_level=INTENT_LEVEL_QUESTION,
        )

        self.assertEqual(plan.toolset, "sistema")
        self.assertEqual(plan.agent, "system_agent")
        self.assertIn("skill sistema", plan.reason)

    def test_procedural_skill_trigger_routes_image_to_vision_capable_agent(self):
        plan = build_decision_plan(
            "analisar imagem",
            {"intent": "respond"},
            intent_level=INTENT_LEVEL_QUESTION,
        )

        self.assertEqual(plan.toolset, "visao")
        self.assertEqual(plan.agent, "browser_agent")
        self.assertIn("skill visao", plan.reason)

    def test_learning_english_routes_to_study_agent(self):
        plan = build_decision_plan(
            "pode me ajudar a aprender ingles?",
            {"intent": "respond"},
            intent_level=INTENT_LEVEL_QUESTION,
            complexity_kind="complex_reasoning",
        )

        self.assertEqual(plan.toolset, "estudos")
        self.assertEqual(plan.agent, "study_agent")
        self.assertEqual(plan.model_policy, "nvidia_or_gemini_for_reasoning")


if __name__ == "__main__":
    unittest.main()
