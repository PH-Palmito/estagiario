import unittest

from core.command_schema import Command
from core.macro_recording import MacroRecordingState, handle_macro_recording


class MacroRecordingTests(unittest.TestCase):
    def test_starts_macro_recording(self):
        result = handle_macro_recording(
            "crie macro briefing rapido",
            MacroRecordingState(False, None, []),
            route=lambda text: {},
            process_action=lambda raw: self.fail("process should not run"),
            add_macro=lambda name, steps: self.fail("add should not run"),
        )

        self.assertTrue(result.handled)
        self.assertTrue(result.state.creating_macro)
        self.assertEqual(result.state.macro_name, "briefing rapido")
        self.assertIn("Criando macro", result.message)

    def test_adds_valid_step(self):
        raw_action = {"intent": "daily_briefing"}
        result = handle_macro_recording(
            "briefing",
            MacroRecordingState(True, "manha", []),
            route=lambda text: raw_action,
            process_action=lambda raw: Command(action="daily_briefing"),
            add_macro=lambda name, steps: self.fail("add should not run"),
        )

        self.assertEqual(result.state.macro_steps, [raw_action])
        self.assertEqual(result.message, "Passo adicionado.")

    def test_blocks_nested_macro_commands(self):
        result = handle_macro_recording(
            "crie macro outra",
            MacroRecordingState(True, "manha", []),
            route=lambda text: {"intent": "start_macro", "target": "outra"},
            process_action=lambda raw: self.fail("process should not run"),
            add_macro=lambda name, steps: self.fail("add should not run"),
        )

        self.assertEqual(result.message, "Esse comando nao pode ser adicionado dentro da macro.")
        self.assertTrue(result.state.creating_macro)

    def test_rejects_invalid_step(self):
        result = handle_macro_recording(
            "comando estranho",
            MacroRecordingState(True, "manha", []),
            route=lambda text: {"intent": "unknown"},
            process_action=lambda raw: "Acao desconhecida",
            add_macro=lambda name, steps: self.fail("add should not run"),
        )

        self.assertEqual(result.message, "Passo invalido: Acao desconhecida")
        self.assertEqual(result.state.macro_steps, [])

    def test_finishes_macro_recording(self):
        saved = {}
        steps = [{"intent": "daily_briefing"}]
        result = handle_macro_recording(
            "fim",
            MacroRecordingState(True, "manha", steps),
            route=lambda text: self.fail("route should not run"),
            process_action=lambda raw: self.fail("process should not run"),
            add_macro=lambda name, macro_steps: saved.update(name=name, steps=macro_steps),
        )

        self.assertEqual(saved, {"name": "manha", "steps": steps})
        self.assertFalse(result.state.creating_macro)
        self.assertEqual(result.message, "Macro 'manha' criada com 1 passos.")


if __name__ == "__main__":
    unittest.main()
