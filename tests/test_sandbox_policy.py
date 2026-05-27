import unittest

from core.command_schema import Command
from core.sandbox_policy import command_sandbox_decision, effective_action_name


class SandboxPolicyTests(unittest.TestCase):
    def test_file_delete_requires_filesystem_confirmation_and_dry_run(self):
        decision = command_sandbox_decision(Command(action="file_delete", params={"path": "x"}))

        self.assertEqual(decision.scope, "filesystem")
        self.assertTrue(decision.requires_confirmation)
        self.assertTrue(decision.dry_run_recommended)

    def test_open_app_is_process_scope_without_confirmation(self):
        decision = command_sandbox_decision(Command(action="open_app", params={"target": "notepad"}))

        self.assertEqual(decision.scope, "process")
        self.assertFalse(decision.requires_confirmation)
        self.assertFalse(decision.dry_run_recommended)

    def test_browser_click_requires_browser_confirmation(self):
        decision = command_sandbox_decision(Command(action="browser_click_text", params={"query": "ok"}))

        self.assertEqual(decision.scope, "browser")
        self.assertTrue(decision.requires_confirmation)

    def test_tool_execute_uses_inner_action_name(self):
        command = Command(action="action_tool_execute", params={"name": "file_replace", "arguments": {}})

        self.assertEqual(effective_action_name(command), "file_replace")
        self.assertEqual(command_sandbox_decision(command).scope, "filesystem")


if __name__ == "__main__":
    unittest.main()
