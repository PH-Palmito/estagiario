import tempfile
import unittest
from pathlib import Path

from core.text_health import find_mojibake_files, text_encoding_health


class TextHealthTests(unittest.TestCase):
    def test_find_mojibake_files_reports_text_markers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "docs").mkdir()
            (root / "docs" / "ok.md").write_text("Tudo certo.", encoding="utf-8")
            (root / "docs" / "bad.md").write_text("Vis\u00c3\u00a3o quebrada.", encoding="utf-8")

            result = find_mojibake_files(root)

        self.assertEqual(result[0]["path"], "docs/bad.md")
        self.assertGreater(result[0]["markers"], 0)

    def test_text_encoding_health_reports_ok_when_clean(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "readme.md").write_text("Texto limpo.", encoding="utf-8")

            result = text_encoding_health(root)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["findings"], [])


if __name__ == "__main__":
    unittest.main()
