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
            self.assertEqual(data["items"][0]["validity"], "durable")
            self.assertEqual(data["items"][0]["expires_at"], 0.0)
            self.assertIn("reason", data["items"][0])

    def test_long_memory_saves_source_validity_confidence_and_reason(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "long_memory.json"
            with (
                patch.object(long_memory, "LONG_MEMORY_PATH", path),
                patch.object(long_memory, "sync_memory_state_safely"),
                patch.object(long_memory, "sync_long_memory_note"),
                patch("memory.long_memory.time.time", return_value=1000.0),
            ):
                created = long_memory.remember_fact(
                    "decidimos priorizar memoria com fontes",
                    category="decision",
                    source="unit",
                    confidence=0.91,
                    validity_days=30,
                    reason="prioridade ativa da lista",
                )
                data = long_memory.load_long_memory()
                formatted = long_memory.format_long_memory()

            self.assertTrue(created)
            item = data["items"][0]
            self.assertEqual(item["source"], "unit")
            self.assertEqual(item["confidence"], 0.91)
            self.assertEqual(item["validity"], "30d")
            self.assertEqual(item["expires_at"], 1000.0 + 30 * 86400)
            self.assertEqual(item["reason"], "prioridade ativa da lista")
            self.assertIn("fonte", formatted)
            self.assertIn("conf 0.91", formatted)
            self.assertIn("validade 30d", formatted)

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

    def test_search_long_memory_ignores_expired_items(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "long_memory.json"
            with (
                patch.object(long_memory, "LONG_MEMORY_PATH", path),
                patch.object(long_memory, "sync_memory_state_safely"),
                patch.object(long_memory, "sync_long_memory_note"),
                patch("memory.long_memory.time.time", return_value=1000.0),
            ):
                long_memory.remember_fact(
                    "contexto temporario sobre carteira",
                    category="context",
                    validity_days=1,
                )
            with (
                patch.object(long_memory, "LONG_MEMORY_PATH", path),
                patch("memory.long_memory.time.time", return_value=1000.0 + 2 * 86400),
            ):
                results = long_memory.search_long_memory("carteira")

            self.assertEqual(results, [])

    def test_clean_long_memory_removes_expired_and_merges_duplicates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "long_memory.json"
            key = long_memory._normalize_key("decision:priorizar memoria com fontes")
            path.write_text(
                """
                {
                  "items": [
                    {
                      "id": "expired",
                      "category": "context",
                      "fact": "contexto vencido sobre teste",
                      "source": "unit",
                      "confidence": 0.5,
                      "expires_at": 1000,
                      "created_at": 1,
                      "updated_at": 1,
                      "seen_count": 1
                    },
                    {
                      "id": "__KEY__",
                      "category": "decision",
                      "fact": "priorizar memoria com fontes",
                      "source": "unit",
                      "confidence": 0.7,
                      "validity": "30d",
                      "expires_at": 0,
                      "created_at": 2,
                      "updated_at": 3,
                      "seen_count": 1
                    },
                    {
                      "id": "__KEY__",
                      "category": "decision",
                      "fact": "priorizar memoria com fontes",
                      "source": "ui-history",
                      "confidence": 0.9,
                      "validity": "30d",
                      "expires_at": 0,
                      "created_at": 4,
                      "updated_at": 5,
                      "seen_count": 2
                    }
                  ]
                }
                """.replace("__KEY__", key),
                encoding="utf-8",
            )
            with (
                patch.object(long_memory, "LONG_MEMORY_PATH", path),
                patch.object(long_memory, "sync_memory_state_safely"),
                patch.object(long_memory, "sync_long_memory_note"),
                patch("memory.long_memory.time.time", return_value=2000.0),
            ):
                report = long_memory.clean_long_memory()
                data = long_memory.load_long_memory()

            self.assertEqual(report["before"], 3)
            self.assertEqual(report["after"], 1)
            self.assertEqual(report["expired_removed"], 1)
            self.assertEqual(report["duplicates_merged"], 1)
            item = data["items"][0]
            self.assertEqual(item["seen_count"], 3)
            self.assertEqual(item["confidence"], 0.9)
            self.assertEqual(item["source"], "unit+ui-history")

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

    def test_operational_context_includes_workspace_context(self):
        with patch.object(operational_context, "load_workspace_context", return_value={
            "available": True,
            "summary": "Contexto do workspace: Projeto Teste.",
            "instructions": ["Rode testes focados."],
            "files": ["AGENTS.md"],
        }):
            payload = operational_context.generate_operational_context()

        self.assertIn("workspace_context", payload)
        self.assertIn("Projeto Teste", payload["summary"])


if __name__ == "__main__":
    unittest.main()
