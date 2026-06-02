import unittest
from unittest.mock import patch

from core.axel_brain import build_axel_brain_decision, format_conversation_brief, format_specialist_brief
from core.router_registry import INTENT_LEVEL_QUESTION


class AxelBrainTests(unittest.TestCase):
    def test_builds_decision_with_specialist_brief(self):
        with (
            patch("core.axel_brain.format_curated_memory", return_value="memoria curta"),
            patch("core.axel_brain.format_relevant_session_memory", return_value="sessoes"),
            patch("core.axel_brain.format_relevant_skills", return_value="skills"),
            patch("core.axel_brain.format_relevant_toolsets", return_value="toolsets"),
        ):
            decision = build_axel_brain_decision(
                "revisar codigo e rodar testes",
                {"intent": "respond"},
                intent_level=INTENT_LEVEL_QUESTION,
                complexity_kind="complex_reasoning",
            )

        self.assertEqual(decision.plan.agent, "dev_agent")
        self.assertEqual(decision.brief.agent, "dev_agent")
        self.assertEqual(decision.brief.toolset, "programacao")
        self.assertEqual(decision.brief.coordination_mode, "single_agent")
        self.assertEqual(decision.brief.tool_libraries[0]["agent"], "dev_agent")
        self.assertEqual(decision.brief.brain_version, "2.0")
        self.assertEqual(decision.brief.memory_layers[0].name, "memoria_curta")
        self.assertIn("Responder", decision.brief.next_step)
        self.assertIn("resposta curta", decision.brief.success_criteria[0])
        self.assertIn("autoavaliacao", decision.brief.post_task_signals[0])
        self.assertIn("memoria curta", decision.brief.context)
        self.assertIn("skills", decision.brief.context)
        self.assertEqual(decision.to_dict()["brief"]["memory_layers"][0]["name"], "memoria_curta")

    def test_builds_multi_agent_brief(self):
        with (
            patch("core.axel_brain.format_curated_memory", return_value="memoria curta"),
            patch("core.axel_brain.format_relevant_session_memory", return_value="sessoes"),
            patch("core.axel_brain.format_relevant_skills", return_value="skills"),
            patch("core.axel_brain.format_relevant_toolsets", return_value="toolsets"),
        ):
            decision = build_axel_brain_decision(
                "pesquisar noticia atual com fontes e revisar codigo",
                {"intent": "respond"},
                intent_level=INTENT_LEVEL_QUESTION,
                complexity_kind="complex_reasoning",
            )

        self.assertEqual(decision.brief.coordination_mode, "multi_agent_handoff")
        self.assertGreaterEqual(len(decision.brief.handoff_chain), 2)

    def test_formats_specialist_brief(self):
        with (
            patch("core.axel_brain.format_curated_memory", return_value="memoria curta"),
            patch("core.axel_brain.format_relevant_session_memory", return_value="sessoes"),
            patch("core.axel_brain.format_relevant_skills", return_value="skills"),
            patch("core.axel_brain.format_relevant_toolsets", return_value="toolsets"),
        ):
            text = format_specialist_brief(
                "noticia atual com fontes",
                {"intent": "respond"},
                intent_level=INTENT_LEVEL_QUESTION,
                complexity_kind="complex_reasoning",
            )

        self.assertIn("AxelBrain escolheu", text)
        self.assertIn("Politica de modelo", text)
        self.assertIn("Proximo passo", text)

    def test_formats_conversation_brief(self):
        with (
            patch("core.axel_brain.format_curated_memory", return_value="memoria curta"),
            patch("core.axel_brain.format_relevant_session_memory", return_value="sessoes"),
            patch("core.axel_brain.format_relevant_skills", return_value="skills"),
            patch("core.axel_brain.format_relevant_toolsets", return_value="toolsets"),
        ):
            text = format_conversation_brief("compare esse codigo", complex_request=True)

        self.assertIn("AxelBrain escolheu", text)
        self.assertIn("Politica de modelo", text)


if __name__ == "__main__":
    unittest.main()
