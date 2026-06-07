import io
import json
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from scripts import axel_action


class AxelActionScriptTests(unittest.TestCase):
    def _run(self, argv):
        output = io.StringIO()
        with redirect_stdout(output):
            code = axel_action.main(argv)
        return code, json.loads(output.getvalue())

    def test_list_command_prints_payload(self):
        with patch.object(axel_action, "action_rpc_catalog", return_value={"ok": True, "actions": []}) as catalog:
            code, payload = self._run(["--list", "--category", "memory"])

        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        catalog.assert_called_once_with("memory")

    def test_execute_command_returns_failure_code_when_blocked(self):
        with patch.object(axel_action, "action_rpc_execute_json", return_value={"ok": False, "error": "bloqueada"}) as execute:
            code, payload = self._run(["memory.backup.create"])

        self.assertEqual(code, 1)
        self.assertFalse(payload["ok"])
        execute.assert_called_once_with("memory.backup.create", "", allow_write=False)

    def test_schema_command(self):
        with patch.object(axel_action, "action_rpc_schema", return_value={"ok": True, "schema": {"name": "x"}}):
            code, payload = self._run(["x", "--schema"])

        self.assertEqual(code, 0)
        self.assertEqual(payload["schema"]["name"], "x")

    def test_execute_command_accepts_key_value_args(self):
        with patch.object(axel_action, "action_rpc_execute", return_value={"ok": True, "message": "ok"}) as execute:
            code, payload = self._run(["memory.backup.list", "--arg", "limit=2"])

        self.assertEqual(code, 0)
        self.assertTrue(payload["ok"])
        execute.assert_called_once_with("memory.backup.list", {"limit": 2}, allow_write=False)

    def test_execute_command_rejects_bad_key_value_arg(self):
        code, payload = self._run(["memory.backup.list", "--arg", "limit"])

        self.assertEqual(code, 1)
        self.assertIn("Argumento invalido", payload["error"])


if __name__ == "__main__":
    unittest.main()
