import unittest

from core.command_schema import Command
from core.direct_response_flow import DirectResponseState, handle_direct_response_flow


class DirectResponseFlowTests(unittest.TestCase):
    def test_accepts_pending_confirmation(self):
        command = Command(action="open_app", params={"target": "notepad"}, requires_confirmation=False)
        result = handle_direct_response_flow(
            "sim",
            DirectResponseState(command, "abrir bloco", None, direct_response_ready_announced=True),
            execute_command=lambda cmd: "Executado.",
            process_action=lambda raw: self.fail("process should not run"),
        )

        self.assertTrue(result.handled)
        self.assertEqual(result.message, "Executado.")
        self.assertIsNone(result.state.pending_command)
        self.assertFalse(result.state.direct_response_ready_announced)

    def test_rejects_smart_open_choice(self):
        result = handle_direct_response_flow(
            "nao",
            DirectResponseState(None, "", "github", direct_response_ready_announced=True),
            execute_command=lambda cmd: self.fail("execute should not run"),
            process_action=lambda raw: self.fail("process should not run"),
        )

        self.assertEqual(result.message, "Ok, nao abri.")
        self.assertIsNone(result.state.pending_smart_open_choice)
        self.assertFalse(result.state.direct_response_ready_announced)

    def test_retries_then_cancels_invalid_smart_open_choice(self):
        first = handle_direct_response_flow(
            "talvez",
            DirectResponseState(None, "", "github"),
            execute_command=lambda cmd: "",
            process_action=lambda raw: "",
        )
        second = handle_direct_response_flow(
            "talvez",
            first.state,
            execute_command=lambda cmd: "",
            process_action=lambda raw: "",
        )

        self.assertEqual(first.message, "Responda com app, site ou cancelar.")
        self.assertEqual(second.message, "Nao consegui entender a resposta. Cancelei essa pergunta.")
        self.assertIsNone(second.state.pending_smart_open_choice)

    def test_executes_smart_open_choice(self):
        seen = {}

        def process(raw):
            seen["raw"] = raw
            return Command(action="smart_open_choice", params=raw["target"])

        result = handle_direct_response_flow(
            "site",
            DirectResponseState(None, "", "github"),
            execute_command=lambda cmd: f"Executado {cmd.params['kind']}.",
            process_action=process,
        )

        self.assertEqual(seen["raw"]["target"], {"name": "github", "kind": "site"})
        self.assertEqual(result.message, "Executado site.")

    def test_simple_invalid_prompt_without_retry_counter(self):
        result = handle_direct_response_flow(
            "talvez",
            DirectResponseState(None, "", "github", pending_smart_open_invalid_attempts=1),
            execute_command=lambda cmd: "",
            process_action=lambda raw: "",
            retry_invalid_smart_open=False,
        )

        self.assertEqual(result.message, "Responda com 'app' ou 'site'.")
        self.assertEqual(result.state.pending_smart_open_invalid_attempts, 1)


if __name__ == "__main__":
    unittest.main()
