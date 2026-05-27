import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import action_memory, long_memory, operational_context


class ContextMemoryFilesTests(unittest.TestCase):
    def test_action_memory_recovers_from_invalid_json_and_remembers_entry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "action_memory.json"
            path.write_text("{invalid", encoding="utf-8")

            with patch.object(action_memory, "MEMORY_PATH", path):
                remembered = action_memory.remember_memory("prefs", "tom", {"style": "curto"}, tags=["voz"])
                recalled = action_memory.recall_memory("prefs", "tom")
                listed = action_memory.list_memory_entries("prefs")

            self.assertTrue(remembered["ok"])
            self.assertEqual(recalled["item"]["value"], {"style": "curto"})
            self.assertEqual(listed["keys"], ["tom"])

    def test_long_memory_recovers_from_invalid_json_and_deduplicates_fact(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "long_memory.json"
            path.write_text("{invalid", encoding="utf-8")

            with (
                patch.object(long_memory, "LONG_MEMORY_PATH", path),
                patch.object(long_memory, "sync_memory_state_safely"),
                patch.object(long_memory, "sync_long_memory_note"),
            ):
                created = long_memory.remember_fact("prefiro respostas curtas e objetivas", category="preference")
                duplicated = long_memory.remember_fact("prefiro respostas curtas e objetivas", category="preference")
                data = long_memory.load_long_memory()

            self.assertTrue(created)
            self.assertFalse(duplicated)
            self.assertEqual(len(data["items"]), 1)
            self.assertEqual(data["items"][0]["seen_count"], 2)

    def test_search_long_memory_scores_relevant_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "long_memory.json"
            with (
                patch.object(long_memory, "LONG_MEMORY_PATH", path),
                patch.object(long_memory, "sync_memory_state_safely"),
                patch.object(long_memory, "sync_long_memory_note"),
            ):
                long_memory.remember_fact("prefiro respostas curtas sobre investimentos", category="preference")
                long_memory.remember_fact("o projeto Axel usa HUD local", category="project")

                results = long_memory.search_long_memory("respostas investimentos", limit=2)

                self.assertEqual(results[0]["category"], "preference")
                self.assertIn("investimentos", results[0]["matched_terms"])
                self.assertGreater(results[0]["score"], 0)

    def test_operational_memory_and_context_use_safe_json_helpers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            memory_path = Path(temp_dir) / "operational_memory.json"
            context_path = Path(temp_dir) / "operational_context.json"
            memory_path.write_text("{invalid", encoding="utf-8")

            with (
                patch.object(operational_context, "OPERATIONAL_MEMORY_PATH", memory_path),
                patch.object(operational_context, "OPERATIONAL_CONTEXT_PATH", context_path),
                patch.object(operational_context, "sync_memory_state_safely"),
                patch.object(operational_context, "sync_operational_context_note"),
                patch.object(operational_context, "save_operational_context", return_value={}),
            ):
                loaded = operational_context.load_operational_memory()
                result = operational_context.remember_operational_preference("usar respostas curtas")
                updated = operational_context.load_operational_memory()

            self.assertEqual(loaded, {"preferences": [], "notes": []})
            self.assertIn("operacional salva", result)
            self.assertEqual(updated["preferences"], ["usar respostas curtas"])


if __name__ == "__main__":
    unittest.main()
