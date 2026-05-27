import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from actions import ensure_default_actions, get_action
from actions.memory_backup_actions import register_memory_backup_actions
from core.command_schema import Command
from core.confirmation import command_requires_strong_confirmation
from core.normalizer import normalize_action
from core.permission_policy import command_risk_level
from core.router_memory import detect_action_core_command
from core.validator import validate_command


class MemoryBackupActionsTests(unittest.TestCase):
    def test_backup_actions_are_registered_with_expected_permissions(self):
        ensure_default_actions()

        create = get_action("memory.backup.create")
        list_action = get_action("memory.backup.list")
        restore = get_action("memory.backup.restore_file")

        self.assertIsNotNone(create)
        self.assertFalse(create.read_only)
        self.assertFalse(create.requires_confirmation)
        self.assertTrue(list_action.read_only)
        self.assertTrue(restore.requires_confirmation)

    def test_router_detects_backup_commands(self):
        self.assertEqual(
            detect_action_core_command("criar backup da memoria"),
            {"intent": "action_tool_execute", "target": {"name": "memory.backup.create", "arguments": {}}},
        )
        self.assertEqual(
            detect_action_core_command("listar backups da memoria"),
            {"intent": "action_tool_execute", "target": {"name": "memory.backup.list", "arguments": {}}},
        )
        self.assertEqual(
            detect_action_core_command("restaurar memoria ui_state.json do memory-20260525-101010"),
            {
                "intent": "action_tool_execute",
                "target": {
                    "name": "memory.backup.restore_file",
                    "arguments": {
                        "filename": "ui_state.json",
                        "backup_name": "memory-20260525-101010",
                    },
                },
            },
        )

    def test_restore_backup_command_requires_strong_confirmation(self):
        ensure_default_actions()
        command = normalize_action(
            {
                "intent": "action_tool_execute",
                "target": {
                    "name": "memory.backup.restore_file",
                    "arguments": {
                        "filename": "ui_state.json",
                        "backup_name": "memory-20260525-101010",
                    },
                },
            }
        )

        ok, error = validate_command(command)

        self.assertTrue(ok, error)
        self.assertTrue(command.requires_confirmation)
        self.assertTrue(command_requires_strong_confirmation(command))
        self.assertEqual(command_risk_level(command), "critical")

    def test_restore_backup_validation_requires_arguments(self):
        ensure_default_actions()
        command = Command(action="action_tool_execute", params={"name": "memory.backup.restore_file", "arguments": {}})

        ok, error = validate_command(command)

        self.assertFalse(ok)
        self.assertIn("backup_name", error)

    def test_backup_actions_execute_against_memory_backup_module(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "ui_state.json").write_text("{}", encoding="utf-8")
            with patch("actions.memory_backup_actions.create_memory_backup") as create_mock:
                create_mock.return_value = type(
                    "Result",
                    (),
                    {
                        "backup_dir": memory / "backups" / "memory-20260525-101010",
                        "copied": ["ui_state.json"],
                        "skipped": [],
                    },
                )()
                register_memory_backup_actions()
                result = get_action("memory.backup.create").handler({})

        self.assertIn("Backup de memoria criado", result)


if __name__ == "__main__":
    unittest.main()
