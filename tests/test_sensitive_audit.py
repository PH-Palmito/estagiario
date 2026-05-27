import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.command_schema import Command
from core.command_service import audit_sensitive_command, should_audit_command
from memory.sensitive_audit import append_sensitive_action_audit


class SensitiveAuditTests(unittest.TestCase):
    def test_should_audit_sensitive_commands_only(self):
        self.assertTrue(should_audit_command(Command(action="file_delete", params={"path": "x"}, requires_confirmation=True)))
        self.assertFalse(should_audit_command(Command(action="open_app", params={"target": "chrome"})))

    def test_append_sensitive_action_audit_writes_jsonl(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "audit.jsonl"

            append_sensitive_action_audit("start", {"action": "file_delete"}, path=path)

            row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(row["event"], "start")
            self.assertEqual(row["data"]["action"], "file_delete")

    def test_audit_sensitive_command_ignores_safe_command(self):
        with patch("core.command_service.append_sensitive_action_audit") as append:
            audit_sensitive_command("start", Command(action="open_app", params={"target": "chrome"}))

        append.assert_not_called()

    def test_audit_sensitive_command_records_permission_payload(self):
        with patch("core.command_service.append_sensitive_action_audit") as append:
            audit_sensitive_command(
                "start",
                Command(action="file_delete", params={"path": "x"}, requires_confirmation=True),
                voice_mode=True,
            )

        payload = append.call_args.args[1]
        self.assertEqual(append.call_args.args[0], "start")
        self.assertEqual(payload["action"], "file_delete")
        self.assertEqual(payload["risk_level"], "critical")
        self.assertTrue(payload["requires_strong_confirmation"])
        self.assertTrue(payload["voice_mode"])


if __name__ == "__main__":
    unittest.main()
