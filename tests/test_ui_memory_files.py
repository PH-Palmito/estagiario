import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import ui_commands, ui_state


class UIMemoryFilesTests(unittest.TestCase):
    def test_ui_state_loads_default_for_invalid_json_and_updates_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "ui_state.json"
            state_path.write_text("{invalid", encoding="utf-8")

            with (
                patch.object(ui_state, "STATE_PATH", state_path),
                patch.object(ui_state, "sync_memory_state_safely"),
            ):
                loaded = ui_state.load_ui_state()
                ui_state.update_ui_state({"visible": True, "last_command": "abrir painel"})
                updated = ui_state.load_ui_state()

            self.assertFalse(loaded["visible"])
            self.assertIn("performance_settings", loaded)
            self.assertEqual(loaded["axel_brain_plan"], {})
            self.assertEqual(loaded["axel_brain_brief"], {})
            self.assertEqual(loaded["axel_brain_contract"], {})
            self.assertEqual(loaded["axel_brain_history"], [])
            self.assertEqual(loaded["axel_brain_timeline"], [])
            self.assertEqual(loaded["axel_brain_history_summary"], {})
            self.assertEqual(loaded["last_route_trace"], {})
            self.assertEqual(loaded["skill_suggestions"], [])
            self.assertIn("observability", loaded)
            self.assertTrue(updated["visible"])
            self.assertEqual(updated["last_command"], "abrir painel")

    def test_ui_state_normalizes_performance_mode_settings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "ui_state.json"

            with (
                patch.object(ui_state, "STATE_PATH", state_path),
                patch.object(ui_state, "sync_memory_state_safely"),
            ):
                ui_state.update_ui_state({"performance_mode": "economia"})
                updated = ui_state.load_ui_state()

            self.assertEqual(updated["performance_mode"], "economy")
            self.assertEqual(updated["performance_settings"]["mode"], "economy")
            self.assertTrue(updated["performance_settings"]["reduce_motion"])

    def test_ui_history_append_preserves_recent_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "ui_state.json"

            with (
                patch.object(ui_state, "STATE_PATH", state_path),
                patch.object(ui_state, "sync_memory_state_safely"),
            ):
                ui_state.append_ui_history("user", "um", max_items=2)
                ui_state.append_ui_history("assistant", "dois", max_items=2)
                ui_state.append_ui_history("user", "tres", max_items=2)
                updated = ui_state.load_ui_state()

            self.assertEqual([item["text"] for item in updated["history"]], ["dois", "tres"])

    def test_ui_notification_append_preserves_recent_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "ui_state.json"

            with (
                patch.object(ui_state, "STATE_PATH", state_path),
                patch.object(ui_state, "sync_memory_state_safely"),
            ):
                ui_state.append_ui_notification("background", "um", max_items=2)
                ui_state.append_ui_notification("background", "dois", level="warning", max_items=2)
                ui_state.append_ui_notification("background", "tres", max_items=2)
                updated = ui_state.load_ui_state()

            self.assertEqual([item["text"] for item in updated["notifications"]], ["dois", "tres"])
            self.assertEqual(updated["notifications"][0]["level"], "warning")

    def test_voice_notification_append_preserves_recent_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "ui_state.json"

            with (
                patch.object(ui_state, "STATE_PATH", state_path),
                patch.object(ui_state, "sync_memory_state_safely"),
            ):
                ui_state.append_voice_notification("um", max_items=2)
                ui_state.append_voice_notification("dois", max_items=2)
                ui_state.append_voice_notification("tres", source="teste", max_items=2)
                updated = ui_state.load_ui_state()

            self.assertEqual([item["text"] for item in updated["voice_notifications_pending"]], ["dois", "tres"])
            self.assertEqual(updated["voice_notifications_pending"][1]["source"], "teste")

    def test_pop_next_voice_notification_returns_and_removes_first_item(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            state_path = Path(temp_dir) / "ui_state.json"

            with (
                patch.object(ui_state, "STATE_PATH", state_path),
                patch.object(ui_state, "sync_memory_state_safely"),
            ):
                ui_state.append_voice_notification("um")
                ui_state.append_voice_notification("dois")
                first = ui_state.pop_next_voice_notification()
                updated = ui_state.load_ui_state()

            self.assertEqual(first["text"], "um")
            self.assertEqual([item["text"] for item in updated["voice_notifications_pending"]], ["dois"])

    def test_ui_commands_queue_preserves_order_and_filters_invalid_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            queue_path = Path(temp_dir) / "ui_commands.json"
            queue_path.write_text('[{"text":"primeiro"}, "ruido"]', encoding="utf-8")

            with patch.object(ui_commands, "QUEUE_PATH", queue_path):
                ui_commands.enqueue_ui_command("segundo", source="test", silent=True)
                first = ui_commands.dequeue_ui_command_item()
                second = ui_commands.dequeue_ui_command_item()
                empty = ui_commands.dequeue_ui_command_item()

            self.assertEqual(first["text"], "primeiro")
            self.assertEqual(second["text"], "segundo")
            self.assertTrue(second["silent"])
            self.assertEqual(empty, {})


if __name__ == "__main__":
    unittest.main()
