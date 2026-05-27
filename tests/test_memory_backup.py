import tempfile
import unittest
from pathlib import Path

from memory.memory_backup import (
    create_memory_backup,
    list_memory_backups,
    memory_backup_summary,
    restore_memory_file,
)


class MemoryBackupTests(unittest.TestCase):
    def test_create_memory_backup_copies_existing_critical_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "ui_state.json").write_text('{"visible": true}', encoding="utf-8")
            (memory / "voice_preferences.json").write_text('{"tts_enabled": false}', encoding="utf-8")

            result = create_memory_backup(root, now=1_700_000_000)

            self.assertTrue(result.backup_dir.name.startswith("memory-20231114-"))
            self.assertIn("ui_state.json", result.copied)
            self.assertIn("voice_preferences.json", result.copied)
            self.assertTrue((result.backup_dir / "manifest.json").exists())

    def test_restore_memory_file_only_allows_critical_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "ui_state.json").write_text('{"visible": true}', encoding="utf-8")
            backup = create_memory_backup(root, now=1_700_000_000)
            (memory / "ui_state.json").write_text('{"visible": false}', encoding="utf-8")

            restored = restore_memory_file("ui_state.json", backup.backup_dir.name, root)

            self.assertEqual(restored.read_text(encoding="utf-8"), '{"visible": true}')
            with self.assertRaises(ValueError):
                restore_memory_file("unsafe.txt", backup.backup_dir.name, root)

    def test_memory_backup_summary_reports_latest_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "ui_state.json").write_text("{}", encoding="utf-8")
            create_memory_backup(root, now=1_700_000_000)

            backups = list_memory_backups(root)
            summary = memory_backup_summary(root)

            self.assertTrue(backups[0]["name"].startswith("memory-20231114-"))
            self.assertEqual(summary["count"], 1)
            self.assertEqual(summary["latest"]["files_count"], 1)


if __name__ == "__main__":
    unittest.main()
