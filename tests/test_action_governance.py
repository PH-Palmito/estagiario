import unittest

from core.action_governance import (
    command_governance_payload,
    command_payload_hash,
)
from core.command_schema import Command


class ActionGovernanceTests(unittest.TestCase):
    def test_sensitive_file_action_describes_governance(self):
        command = Command(action="file_delete", params={"path": "x"}, requires_confirmation=True)

        payload = command_governance_payload(command)

        self.assertEqual(payload["action_class"], "sensitive_write")
        self.assertEqual(len(payload["payload_hash"]), 16)
        self.assertFalse(payload["reversible"])
        self.assertEqual(payload["target"], "x")
        self.assertEqual(payload["decision"], "confirm_strong")
        self.assertTrue(payload["audit_required"])

    def test_read_action_describes_allow_read_decision(self):
        command = Command(action="weather_summary", params={"location": "Salvador"})

        payload = command_governance_payload(command)

        self.assertEqual(payload["action_class"], "read")
        self.assertTrue(payload["reversible"])
        self.assertEqual(payload["target"], "Salvador")
        self.assertEqual(payload["decision"], "allow_read")
        self.assertFalse(payload["audit_required"])

    def test_payload_hash_is_stable_for_param_order(self):
        first = Command(action="file_delete", params={"path": "x", "force": True})
        second = Command(action="file_delete", params={"force": True, "path": "x"})

        self.assertEqual(command_payload_hash(first), command_payload_hash(second))


if __name__ == "__main__":
    unittest.main()
