import unittest

from core.command_schema import Command
from core.intent_judge import judge_command_interpretation


class IntentJudgeTests(unittest.TestCase):
    def test_blocks_investment_action_for_project_memory_text(self):
        result = judge_command_interpretation(
            'axel guarde a ideia de projeto "criar um aplicativo de devocional"',
            Command(action="investment_refresh_public_wallet", params={}),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "investment_action_without_investment_terms")
        self.assertIn("Segurei essa ação", result.message)
        self.assertIn("rotinas financeiras", result.message)

    def test_allows_investment_action_for_wallet_text(self):
        result = judge_command_interpretation(
            "atualizar carteira",
            Command(action="investment_refresh_public_wallet", params={}),
        )

        self.assertTrue(result.allowed)

    def test_allows_investment_answer_for_ticker_question(self):
        result = judge_command_interpretation(
            "como o el nino afeta o VGIA11?",
            Command(action="investment_memory_answer", params={"question": "como o el nino afeta o VGIA11?"}),
        )

        self.assertTrue(result.allowed)

    def test_blocks_unrequested_open_app(self):
        result = judge_command_interpretation(
            "guarde essa ideia",
            Command(action="open_app", params={"target": "epic games"}),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "open_action_without_open_intent")
        self.assertIn("Segurei a abertura", result.message)

    def test_blocks_screen_action_for_general_question(self):
        result = judge_command_interpretation(
            "oq faz o estagiario noturno",
            Command(action="browser_describe_screen", params={}),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "screen_action_for_general_question")
        self.assertIn("Segurei a leitura da tela", result.message)


if __name__ == "__main__":
    unittest.main()
