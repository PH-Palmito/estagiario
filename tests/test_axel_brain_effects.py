import unittest

from core.axel_brain_effects import (
    apply_plan_to_command,
    format_axel_brain_effects,
    personality_allowed_for_plan,
)
from core.command_schema import Command


class AxelBrainEffectsTests(unittest.TestCase):
    def test_plan_applies_confirmation_and_confidence_to_command(self):
        command = Command(action="close_app", confidence=0.9)

        effects = apply_plan_to_command(
            command,
            {"needs_confirmation": True, "confidence": 0.62, "agent": "system_agent", "toolset": "sistema"},
        )

        self.assertTrue(command.requires_confirmation)
        self.assertEqual(command.confidence, 0.62)
        self.assertTrue(effects["confirmation_applied"])
        self.assertTrue(effects["confidence_applied"])

    def test_sensitive_and_short_modes_suppress_personality(self):
        self.assertFalse(personality_allowed_for_plan({"response_mode": "execute_short", "risk_level": "low"}))
        self.assertFalse(personality_allowed_for_plan({"response_mode": "answer_with_context", "risk_level": "critical"}))
        self.assertTrue(personality_allowed_for_plan({"response_mode": "answer_with_context", "risk_level": "read"}))

    def test_effect_report_exposes_active_runtime_links(self):
        text = format_axel_brain_effects(
            {
                "agent": "study_agent",
                "toolset": "estudos",
                "model_policy": "nvidia_or_gemini_for_reasoning",
                "needs_confirmation": False,
                "response_mode": "answer_with_context",
                "tool_libraries": [{"actions": [{"name": "study.analyze_files"}]}],
            },
            {"memory_layers": [{"name": "skills_procedurais"}]},
            {"channel": "local"},
        )

        self.assertIn("study_agent", text)
        self.assertIn("1 actions candidatas", text)
        self.assertIn("skills_procedurais", text)
        self.assertIn("personalidade liberada", text)

    def test_effect_report_counts_tuple_tool_libraries(self):
        text = format_axel_brain_effects(
            {
                "tool_libraries": ({"actions": ({"name": "file_delete"},)},),
                "response_mode": "confirm_then_act",
                "risk_level": "critical",
            },
            {},
            {},
        )

        self.assertIn("1 actions candidatas", text)


if __name__ == "__main__":
    unittest.main()
