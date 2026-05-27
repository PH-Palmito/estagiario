import unittest

from core.intent_complexity import COMPLEX_REASONING, SIMPLE_COMMAND, classify_intent_complexity, text_looks_complex
from core.router_registry import (
    INTENT_LEVEL_COMPOSITE_TASK,
    INTENT_LEVEL_CONVERSATION,
    INTENT_LEVEL_DIRECT_COMMAND,
    INTENT_LEVEL_QUESTION,
)


class IntentComplexityTests(unittest.TestCase):
    def test_direct_command_is_simple_by_default(self):
        result = classify_intent_complexity(
            "abrir chrome",
            intent_level=INTENT_LEVEL_DIRECT_COMMAND,
            raw_action={"intent": "open_app"},
        )

        self.assertEqual(result.kind, SIMPLE_COMMAND)
        self.assertFalse(result.should_use_llm)

    def test_composite_task_requests_planning(self):
        result = classify_intent_complexity(
            "abra chrome e depois toque spotify",
            intent_level=INTENT_LEVEL_COMPOSITE_TASK,
            raw_action={"intent": "run_routine"},
        )

        self.assertEqual(result.kind, COMPLEX_REASONING)
        self.assertTrue(result.should_plan)

    def test_complex_question_uses_llm(self):
        result = classify_intent_complexity(
            "compare esse cenario e explique o que vale a pena",
            intent_level=INTENT_LEVEL_QUESTION,
            raw_action={"intent": "respond"},
        )

        self.assertEqual(result.kind, COMPLEX_REASONING)
        self.assertTrue(result.should_use_llm)

    def test_short_question_can_stay_simple(self):
        result = classify_intent_complexity(
            "que horas sao",
            intent_level=INTENT_LEVEL_QUESTION,
            raw_action={"intent": "time"},
        )

        self.assertEqual(result.kind, SIMPLE_COMMAND)
        self.assertFalse(result.should_use_llm)

    def test_conversation_uses_llm_but_marks_simple_when_short(self):
        result = classify_intent_complexity(
            "bom dia",
            intent_level=INTENT_LEVEL_CONVERSATION,
            raw_action={"intent": "respond"},
        )

        self.assertEqual(result.kind, SIMPLE_COMMAND)
        self.assertTrue(result.should_use_llm)

    def test_text_looks_complex_for_long_request(self):
        self.assertTrue(
            text_looks_complex(
                "quero que voce avalie essa ideia com calma considerando riscos custos beneficios e proximos passos"
            )
        )


if __name__ == "__main__":
    unittest.main()
