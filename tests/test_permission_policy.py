import unittest

from actions import ActionSpec, register_action
from core.command_schema import Command
from core.permission_policy import (
    RiskLevel,
    action_requires_confirmation,
    command_requires_confirmation,
    command_risk_level,
    command_requires_strong_confirmation,
    execution_permission,
    permission_decision,
    tool_name_for_command,
)


class PermissionPolicyTests(unittest.TestCase):
    def test_direct_sensitive_command_requires_strong_confirmation(self):
        command = Command(action="file_delete", params={"path": "x"}, requires_confirmation=True)

        decision = permission_decision(command)

        self.assertTrue(command_requires_confirmation(command))
        self.assertTrue(command_requires_strong_confirmation(command))
        self.assertEqual(command_risk_level(command), RiskLevel.CRITICAL)
        self.assertTrue(decision.requires_strong_confirmation)
        self.assertEqual(decision.sandbox_scope, "filesystem")
        self.assertTrue(decision.dry_run_recommended)
        self.assertFalse(execution_permission(command).allowed)
        self.assertTrue(execution_permission(command, confirmed=True).allowed)

    def test_tool_command_inherits_registered_confirmation(self):
        register_action(
            ActionSpec(
                name="unit.policy_sensitive",
                description="Action de teste.",
                handler=lambda _args: "ok",
                category="system",
                read_only=False,
                requires_confirmation=True,
            )
        )
        command = Command(
            action="action_tool_execute",
            params={"name": "unit.policy_sensitive", "arguments": {}},
        )

        decision = permission_decision(command)

        self.assertEqual(tool_name_for_command(command), "unit.policy_sensitive")
        self.assertTrue(action_requires_confirmation("unit.policy_sensitive"))
        self.assertTrue(command_requires_confirmation(command))
        self.assertTrue(command_requires_strong_confirmation(command))
        self.assertEqual(decision.risk_level, RiskLevel.HIGH)
        self.assertFalse(decision.read_only)
        self.assertEqual(decision.category, "system")
        self.assertEqual(decision.sandbox_scope, "read_only")

    def test_registered_investment_mutation_requires_strong_confirmation(self):
        register_action(
            ActionSpec(
                name="unit.policy_write",
                description="Action de teste.",
                handler=lambda _args: "ok",
                category="investments",
                read_only=False,
                requires_confirmation=True,
            )
        )
        command = Command(action="unit.policy_write", params={}, requires_confirmation=True)

        self.assertTrue(command_requires_confirmation(command))
        self.assertTrue(command_requires_strong_confirmation(command))
        self.assertEqual(command_risk_level(command), RiskLevel.HIGH)

    def test_non_sensitive_registered_command_only_needs_standard_confirmation(self):
        register_action(
            ActionSpec(
                name="unit.policy_standard_write",
                description="Action de teste.",
                handler=lambda _args: "ok",
                category="unit",
                read_only=False,
                requires_confirmation=True,
            )
        )
        command = Command(action="unit.policy_standard_write", params={}, requires_confirmation=True)

        self.assertTrue(command_requires_confirmation(command))
        self.assertFalse(command_requires_strong_confirmation(command))
        self.assertEqual(command_risk_level(command), RiskLevel.MEDIUM)

    def test_read_only_command_has_read_risk(self):
        register_action(
            ActionSpec(
                name="unit.policy_read",
                description="Action de teste.",
                handler=lambda _args: "ok",
                category="unit",
                read_only=True,
                requires_confirmation=False,
            )
        )
        command = Command(action="unit.policy_read", params={})

        decision = permission_decision(command)

        self.assertTrue(decision.read_only)
        self.assertEqual(decision.risk_level, RiskLevel.READ)
        self.assertTrue(execution_permission(command).allowed)


if __name__ == "__main__":
    unittest.main()
