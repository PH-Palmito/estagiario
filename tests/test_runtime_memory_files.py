import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import assistant_phrases, current_topic, macros, vision_history


class RuntimeMemoryFilesTests(unittest.TestCase):
    def test_current_topic_recovers_invalid_json_and_saves_topic(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "current_topic.json"
            path.write_text("{invalid", encoding="utf-8")

            with (
                patch.object(current_topic, "TOPIC_PATH", path),
                patch.object(current_topic, "fetch_memory_payload_safely", return_value={}),
                patch.object(current_topic, "sync_memory_state_safely"),
                patch.object(current_topic, "sync_current_topic_note"),
            ):
                self.assertEqual(current_topic.load_current_topic(), {})
                saved = current_topic.save_current_topic({"topic": "Axel", "summary": "Projeto local"})
                loaded = current_topic.load_current_topic()

            self.assertEqual(saved["topic"], "Axel")
            self.assertEqual(loaded["summary"], "Projeto local")
            self.assertIn("updated_at", loaded)

    def test_vision_history_recovers_invalid_json_and_keeps_recent_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "vision_history.json"
            path.write_text("{invalid", encoding="utf-8")

            with (
                patch.object(vision_history, "HISTORY_PATH", path),
                patch.object(vision_history, "sync_memory_state_safely"),
                patch.object(vision_history, "update_current_topic_from_vision"),
            ):
                self.assertEqual(vision_history.load_vision_history(), [])
                vision_history.remember_vision_analysis("tela", "grafico subiu", {"page_title": "Dashboard"})
                loaded = vision_history.load_vision_history()

            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0]["summary"], "gráfico subiu")

    def test_macros_recover_invalid_json_and_update_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "macros.json"
            path.write_text("{invalid", encoding="utf-8")

            with patch.object(macros, "FILE", path):
                self.assertEqual(macros.load_macros(), {})
                macros.add_macro("Manha", [{"intent": "daily_briefing"}])
                self.assertEqual(macros.get_macro("manha"), [{"intent": "daily_briefing"}])
                self.assertTrue(macros.delete_macro("manha"))
                self.assertEqual(macros.list_macros(), [])

    def test_assistant_phrase_state_recovers_invalid_json(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "assistant_phrase_state.json"
            path.write_text("{invalid", encoding="utf-8")

            with patch.object(assistant_phrases, "PHRASE_STATE_PATH", path):
                choice = assistant_phrases.next_phrase("unit", ("um", "dois"), default="x")
                state = assistant_phrases._load_phrase_state()

            self.assertIn(choice, {"um", "dois"})
            self.assertIn("recent", state)


if __name__ == "__main__":
    unittest.main()
