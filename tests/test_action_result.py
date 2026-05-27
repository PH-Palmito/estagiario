import unittest

from actions.registry import ActionSpec, execute_action, execute_action_result, register_action
from core.action_result import ActionResult, normalize_action_result


class ActionResultTests(unittest.TestCase):
    def test_success_result_keeps_message_and_metadata(self):
        result = ActionResult.ok("feito", data={"id": 1})

        self.assertTrue(result.success)
        self.assertEqual(result.message, "feito")
        self.assertEqual(result.data, {"id": 1})
        self.assertEqual(str(result), "feito")

    def test_failed_result_keeps_error(self):
        result = ActionResult.failed("falhou", error="boom")

        self.assertFalse(result.success)
        self.assertEqual(result.message, "falhou")
        self.assertEqual(result.error, "boom")

    def test_normalize_legacy_string_result(self):
        result = normalize_action_result("ok legado")

        self.assertTrue(result.success)
        self.assertEqual(result.message, "ok legado")

    def test_normalize_existing_result(self):
        original = ActionResult.ok("ok")

        self.assertIs(normalize_action_result(original), original)

    def test_registry_exposes_structured_action_result(self):
        register_action(
            ActionSpec(
                name="unit.structured_result",
                description="Action de teste.",
                handler=lambda _args: ActionResult.ok("feito", data={"source": "test"}),
            )
        )

        legacy = execute_action("unit.structured_result")
        structured = execute_action_result("unit.structured_result")

        self.assertEqual(legacy, "feito")
        self.assertTrue(structured.success)
        self.assertEqual(structured.data, {"source": "test"})


if __name__ == "__main__":
    unittest.main()
