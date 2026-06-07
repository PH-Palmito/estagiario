import json
import unittest

from actions import ActionSpec, ensure_default_actions, register_action
from core.action_rpc import (
    action_rpc_catalog,
    action_rpc_execute,
    action_rpc_execute_json,
    action_rpc_schema,
    format_action_rpc_payload,
)


class ActionRpcTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ensure_default_actions()
        register_action(
            ActionSpec(
                name="unit.rpc_echo",
                description="Ecoa texto.",
                handler=lambda args: "Eco: " + str(args.get("text") or ""),
                category="unit",
                read_only=True,
                parameters={"text": {"type": "string", "description": "Texto."}},
            )
        )
        register_action(
            ActionSpec(
                name="unit.rpc_write",
                description="Action de escrita para teste.",
                handler=lambda _args: "Escrevi.",
                category="unit",
                read_only=False,
            )
        )

    def test_catalog_lists_registered_actions(self):
        result = action_rpc_catalog("unit")

        self.assertTrue(result["ok"])
        self.assertIn("unit.rpc_echo", [item["name"] for item in result["actions"]])

    def test_schema_returns_tool_schema(self):
        result = action_rpc_schema("unit.rpc_echo")

        self.assertTrue(result["ok"])
        self.assertEqual(result["schema"]["name"], "unit.rpc_echo")

    def test_execute_read_only_action(self):
        result = action_rpc_execute("unit.rpc_echo", {"text": "oi"})

        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], "Eco: oi")

    def test_product_cache_actions_are_read_only(self):
        catalog = action_rpc_catalog("browser")
        names = [item["name"] for item in catalog["actions"]]

        self.assertIn("browser_products_cache", names)
        self.assertIn("browser_products_cheapest_cache", names)

    def test_investment_daily_report_action_is_read_only(self):
        catalog = action_rpc_catalog("investments")
        daily = next(item for item in catalog["actions"] if item["name"] == "investment_daily_report")

        self.assertTrue(daily["read_only"])

    def test_execute_blocks_write_by_default(self):
        result = action_rpc_execute("unit.rpc_write", {})

        self.assertFalse(result["ok"])
        self.assertIn("bloqueada", result["error"])

    def test_execute_allows_write_when_explicit(self):
        result = action_rpc_execute("unit.rpc_write", {}, allow_write=True)

        self.assertTrue(result["ok"])
        self.assertEqual(result["message"], "Escrevi.")

    def test_execute_json_rejects_invalid_payload(self):
        result = action_rpc_execute_json("unit.rpc_echo", "{invalid")

        self.assertFalse(result["ok"])
        self.assertIn("JSON invalido", result["error"])

    def test_format_payload_is_json(self):
        raw = format_action_rpc_payload({"ok": True, "x": 1})

        self.assertEqual(json.loads(raw)["x"], 1)


if __name__ == "__main__":
    unittest.main()
