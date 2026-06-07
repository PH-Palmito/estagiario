import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from memory import agenda, reminders, voice_preferences


class CoreMemoryFilesTests(unittest.TestCase):
    def test_agenda_handles_invalid_json_and_updates_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "agenda.json"
            path.write_text("{invalid", encoding="utf-8")

            with patch.object(agenda, "AGENDA_PATH", path):
                self.assertIn("livre", agenda.list_agenda_today())
                added = agenda.add_agenda_item("hoje revisar arquitetura")
                listed = agenda.list_agenda_today()
                removed = agenda.remove_agenda_item("1")

            self.assertIn("Compromisso registrado", added)
            self.assertIn("revisar arquitetura", listed)
            self.assertIn("Removi da agenda", removed)

    def test_agenda_timed_items_join_due_alert_flow(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "agenda.json"
            base = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)

            with patch.object(agenda, "AGENDA_PATH", path):
                added = agenda.add_agenda_item("hoje as 09:30 revisar PR")
                listed = agenda.list_agenda_today()
                due = agenda.consume_due_agenda_items(base.replace(hour=9, minute=31))
                due_again = agenda.consume_due_agenda_items(base.replace(hour=9, minute=40))

            self.assertIn("09:30", added)
            self.assertIn("09:30 - revisar PR", listed)
            self.assertEqual(due[0]["text"], "revisar PR")
            self.assertEqual(due[0]["source"], "agenda")
            self.assertEqual(due_again, [])

    def test_agenda_exports_and_imports_ics(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "agenda.json"
            ics_path = Path(temp_dir) / "agenda.ics"

            with (
                patch.object(agenda, "AGENDA_PATH", path),
                patch.object(agenda, "AGENDA_ICS_EXPORT_PATH", ics_path),
                patch.object(agenda, "_today", return_value=datetime(2026, 6, 7).date()),
            ):
                agenda.add_agenda_item("hoje as 10:00 revisar calendario")
                exported = agenda.export_agenda_ics()
                path.unlink()
                imported = agenda.import_agenda_ics(ics_path)
                listed = agenda.list_agenda_today()

            self.assertIn("Exportei 1 compromisso", exported)
            self.assertIn("Importei 1 compromisso", imported)
            self.assertIn("10:00 - revisar calendario", listed)

    def test_reminders_handle_invalid_json_and_consume_due_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "reminders.json"
            path.write_text("{invalid", encoding="utf-8")
            with (
                patch.object(reminders, "REMINDERS_PATH", path),
                patch.object(reminders, "sync_memory_state_safely"),
                patch.object(reminders, "load_current_topic", return_value={}),
            ):
                self.assertEqual(reminders.load_reminders(), {"items": []})
                result = reminders.add_reminder("em 1 minuto beber agua")
                due = reminders.consume_due_reminders(datetime.now() + timedelta(minutes=2))
                pending = reminders.list_reminders()

            self.assertIn("Vou lembrar", result)
            self.assertEqual(len(due), 1)
            self.assertEqual(due[0]["text"], "beber agua")
            self.assertIn("Nao ha lembretes pendentes", pending)

    def test_voice_preferences_merge_defaults_and_update_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "voice_preferences.json"
            path.write_text("{invalid", encoding="utf-8")

            with (
                patch.object(voice_preferences, "FILE", path),
                patch.object(voice_preferences, "sync_memory_state_safely"),
            ):
                defaults = voice_preferences.load_voice_preferences()
                updated = voice_preferences.update_voice_preferences({"tts_enabled": False, "assistant_style": "seco"})
                loaded = voice_preferences.load_voice_preferences()

            self.assertEqual(defaults["hotword"], "estagiario")
            self.assertFalse(updated["tts_enabled"])
            self.assertEqual(loaded["assistant_style"], "seco")
            self.assertIn("chat_model", loaded)


if __name__ == "__main__":
    unittest.main()
