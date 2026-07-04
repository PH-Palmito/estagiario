import unittest
from unittest.mock import patch

from core.command_schema import Command
from core.intent_llm_judge import (
    llm_review_to_judge_result,
    review_intent_with_llm,
    should_request_llm_intent_review,
)


class IntentLlmJudgeTests(unittest.TestCase):
    def test_disabled_by_default(self):
        with patch("core.intent_llm_judge.load_ui_state", return_value={"llm_intent_judge_enabled": False}):
            self.assertFalse(
                should_request_llm_intent_review(
                    "abra chrome",
                    Command(action="open_app", params={"target": "chrome"}),
                )
            )

    def test_enabled_reviews_risky_action(self):
        with patch("core.intent_llm_judge.load_ui_state", return_value={"llm_intent_judge_enabled": True}):
            self.assertTrue(
                should_request_llm_intent_review(
                    "abra chrome",
                    Command(action="open_app", params={"target": "chrome"}),
                )
            )

    def test_enabled_skips_clear_read_only_investment_answer(self):
        with patch("core.intent_llm_judge.load_ui_state", return_value={"llm_intent_judge_enabled": True}):
            self.assertFalse(
                should_request_llm_intent_review(
                    "como o el nino afeta o VGIA11?",
                    Command(action="investment_memory_answer", params={"question": "como o el nino afeta o VGIA11?"}),
                )
            )

    def test_review_parses_block_json(self):
        review = review_intent_with_llm(
            "guarde ideia",
            Command(action="open_app", params={"target": "epic games"}),
            ask_model_fn=lambda *args, **kwargs: '{"verdict":"block","reason":"acao nao combina","message":"Nao vou abrir app para esse pedido."}',
        )

        result = llm_review_to_judge_result(review)

        self.assertFalse(result.allowed)
        self.assertIn("acao nao combina", result.reason)
        self.assertIn("Nao vou abrir", result.message)

    def test_review_parses_confirm_json(self):
        review = review_intent_with_llm(
            "fecha isso",
            Command(action="close_app", params={"target": "chrome"}),
            ask_model_fn=lambda *args, **kwargs: '{"verdict":"confirm","reason":"alvo implicito","message":"Confirmo fechar Chrome?"}',
        )

        result = llm_review_to_judge_result(review)

        self.assertTrue(result.allowed)
        self.assertTrue(result.requires_confirmation)
        self.assertIn("alvo implicito", result.reason)


if __name__ == "__main__":
    unittest.main()
