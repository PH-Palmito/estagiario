import unittest
from pathlib import Path


class StartupVerificationDocTests(unittest.TestCase):
    def test_startup_verification_doc_records_reboot_criteria(self):
        content = Path("docs/axel-startup-verification.md").read_text(encoding="utf-8")

        self.assertIn("Depois de reiniciar", content)
        self.assertIn(".tmp/axel-startup.log", content)
        self.assertIn("Axel abriu automaticamente apos o reboot real", content)


if __name__ == "__main__":
    unittest.main()
