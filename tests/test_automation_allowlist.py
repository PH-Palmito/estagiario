import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from memory import automation_allowlist


class AutomationAllowlistTests(unittest.TestCase):
    def test_add_load_and_check_trusted_automation(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "automation_allowlist.json"
            with patch.object(automation_allowlist, "AUTOMATION_ALLOWLIST_PATH", path):
                automation_allowlist.add_trusted_automation(" Rotina Programacao ")
                automation_allowlist.add_trusted_automation("rotina programacao")

                self.assertEqual(automation_allowlist.load_trusted_automations(), ["rotina programacao"])
                self.assertTrue(automation_allowlist.is_trusted_automation("ROTINA   PROGRAMACAO"))

    def test_remove_trusted_automation(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "automation_allowlist.json"
            with patch.object(automation_allowlist, "AUTOMATION_ALLOWLIST_PATH", path):
                automation_allowlist.add_trusted_automation("rotina foco")

                self.assertTrue(automation_allowlist.remove_trusted_automation("rotina foco"))
                self.assertFalse(automation_allowlist.is_trusted_automation("rotina foco"))

    def test_empty_name_is_ignored(self):
        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "automation_allowlist.json"
            with patch.object(automation_allowlist, "AUTOMATION_ALLOWLIST_PATH", path):
                result = automation_allowlist.add_trusted_automation(" ")

                self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
