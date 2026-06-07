import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import obsidian_sync


class ObsidianSyncTests(unittest.TestCase):
    def test_sync_long_memory_note_includes_memory_metadata(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            vault = Path(temp_dir)
            payload = {
                "updated_at": 1000.0,
                "items": [
                    {
                        "category": "decision",
                        "fact": "priorizar memoria com fontes",
                        "source": "unit",
                        "confidence": 0.91,
                        "validity": "30d",
                        "reason": "prioridade ativa",
                    }
                ],
            }

            with (
                patch.object(obsidian_sync, "OBSIDIAN_SYNC_ENABLED", True),
                patch.object(obsidian_sync, "OBSIDIAN_VAULT_PATH", str(vault)),
            ):
                ok = obsidian_sync.sync_long_memory_note(payload)

            note = vault / "Axel" / "Long Memory.md"
            content = note.read_text(encoding="utf-8")

        self.assertTrue(ok)
        self.assertIn("priorizar memoria com fontes", content)
        self.assertIn("fonte: unit", content)
        self.assertIn("confianca: 0.91", content)
        self.assertIn("validade: 30d", content)
        self.assertIn("motivo: prioridade ativa", content)


if __name__ == "__main__":
    unittest.main()
