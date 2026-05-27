import unittest

from core.command_schema import Command
from core.confirmation import (
    command_requires_strong_confirmation,
    confirmation_prompt,
    is_confirmation_accepted,
    is_confirmation_rejected,
)
from core.confirmation_flow import handle_pending_confirmation


class ConfirmationPolicyTests(unittest.TestCase):
    def test_file_delete_requires_literal_confirmation(self):
        command = Command(action="file_delete", params={"path": "teste.txt"}, requires_confirmation=True)

        self.assertTrue(command_requires_strong_confirmation(command))
        self.assertFalse(is_confirmation_accepted("sim", command))
        self.assertTrue(is_confirmation_accepted("confirmar", command))
        self.assertIn("responda exatamente: confirmar", confirmation_prompt(command))

    def test_run_script_requires_literal_confirmation(self):
        command = Command(action="run_script", params={"target": "scripts/teste.py"}, requires_confirmation=True)

        self.assertTrue(command_requires_strong_confirmation(command))
        self.assertFalse(is_confirmation_accepted("pode sim", command))
        self.assertFalse(is_confirmation_accepted("confirmo", command))
        self.assertTrue(is_confirmation_accepted("confirmar", command))

    def test_action_tool_execute_inherits_strong_policy_for_sensitive_tool(self):
        command = Command(
            action="action_tool_execute",
            params={"name": "file_write", "arguments": {"path": "teste.txt", "content": "oi"}},
            requires_confirmation=True,
        )

        self.assertTrue(command_requires_strong_confirmation(command))
        self.assertFalse(is_confirmation_accepted("sim", command))
        self.assertTrue(is_confirmation_accepted("confirmar", command))

    def test_investment_mutation_requires_literal_confirmation(self):
        command = Command(action="investment_add_watchlist", params={"ticker": "BBAS3"}, requires_confirmation=True)

        self.assertTrue(command_requires_strong_confirmation(command))
        self.assertFalse(is_confirmation_accepted("sim", command))
        self.assertTrue(is_confirmation_accepted("confirmar", command))

    def test_light_confirmation_still_accepts_sim(self):
        command = Command(action="unit.light_confirmation", params={}, requires_confirmation=True)

        self.assertFalse(command_requires_strong_confirmation(command))
        self.assertTrue(is_confirmation_accepted("sim", command))
        self.assertTrue(is_confirmation_accepted("confirmo", command))

    def test_confirmation_rejection_accepts_cancel_variants(self):
        self.assertTrue(is_confirmation_rejected("deixa quieto"))
        self.assertTrue(is_confirmation_rejected("cancele isso"))

    def test_pending_confirmation_executes_and_clears_state(self):
        command = Command(action="investment_add_watchlist", params={"ticker": "BBAS3"}, requires_confirmation=True)
        remembered = []

        result = handle_pending_confirmation(
            "confirmar",
            command,
            "adicione BBAS3",
            lambda executed: f"executed:{executed.action}",
            remembered.append,
        )

        self.assertTrue(result.handled)
        self.assertTrue(result.accepted)
        self.assertIsNone(result.pending_command)
        self.assertEqual(result.pending_learning_text, "")
        self.assertEqual(result.message, "executed:investment_add_watchlist")
        self.assertEqual(remembered, [command])

    def test_pending_confirmation_cancel_clears_state(self):
        command = Command(action="investment_add_watchlist", params={"ticker": "BBAS3"}, requires_confirmation=True)

        result = handle_pending_confirmation(
            "deixa quieto",
            command,
            "adicione BBAS3",
            lambda _command: "nao deveria executar",
        )

        self.assertTrue(result.handled)
        self.assertTrue(result.cancelled)
        self.assertIsNone(result.pending_command)
        self.assertEqual(result.pending_learning_text, "")
        self.assertEqual(result.message, "Acao cancelada.")

    def test_pending_confirmation_keeps_state_when_answer_is_invalid(self):
        command = Command(action="file_delete", params={"path": "teste.txt"}, requires_confirmation=True)

        result = handle_pending_confirmation(
            "pode sim",
            command,
            "delete teste",
            lambda _command: "nao deveria executar",
        )

        self.assertTrue(result.handled)
        self.assertFalse(result.accepted)
        self.assertFalse(result.cancelled)
        self.assertEqual(result.pending_command, command)
        self.assertEqual(result.pending_learning_text, "delete teste")
        self.assertIn("confirmar", result.message)


if __name__ == "__main__":
    unittest.main()
