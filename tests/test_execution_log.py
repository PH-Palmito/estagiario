import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from memory.execution_log import append_execution_log


class ExecutionLogTests(unittest.TestCase):
    def test_append_execution_log_redacts_sensitive_keys_and_text(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "execution_log.jsonl"

            with patch("memory.execution_log.EXECUTION_LOG_PATH", path):
                append_execution_log(
                    "network_call",
                    {
                        "action": "telegram_status",
                        "api_key": "abc123456789",
                        "headers": {"Authorization": "Bearer secret-token-123456789"},
                        "message": "contato pedro@example.com token=abc123456789 cpf 123.456.789-00",
                        "nested": [{"refresh_token": "refresh-123456789"}],
                    },
                )

            row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

        data = row["data"]
        self.assertEqual(data["action"], "telegram_status")
        self.assertEqual(data["api_key"], "[redacted]")
        self.assertEqual(data["headers"]["Authorization"], "[redacted]")
        self.assertEqual(data["nested"][0]["refresh_token"], "[redacted]")
        self.assertIn("[email]", data["message"])
        self.assertIn("token=[redacted]", data["message"])
        self.assertIn("[number]", data["message"])
        self.assertNotIn("pedro@example.com", data["message"])
        self.assertNotIn("123.456.789-00", data["message"])

    def test_append_execution_log_keeps_regular_structured_payload(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "execution_log.jsonl"

            with patch("memory.execution_log.EXECUTION_LOG_PATH", path):
                append_execution_log(
                    "command_execute_end",
                    {"action": "open_app", "duration_ms": 123.4, "success": True},
                )

            row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(row["event"], "command_execute_end")
        self.assertEqual(row["data"]["action"], "open_app")
        self.assertEqual(row["data"]["duration_ms"], 123.4)
        self.assertTrue(row["data"]["success"])


if __name__ == "__main__":
    unittest.main()
