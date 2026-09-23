import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from memory import adaptive_preferences, deep_memory, operational_context, voice_preferences
from memory.json_store import write_json_atomic


class DeepMemoryTests(unittest.TestCase):
    def _isolated_paths(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        root = Path(tmpdir.name)
        patches = [
            patch.object(voice_preferences, "FILE", root / "voice_preferences.json"),
            patch.object(adaptive_preferences, "ADAPTIVE_PREFERENCES_PATH", root / "adaptive_preferences.json"),
            patch.object(operational_context, "OPERATIONAL_MEMORY_PATH", root / "operational_memory.json"),
            patch.object(operational_context, "OPERATIONAL_CONTEXT_PATH", root / "operational_context.json"),
        ]
        return root, patches

    def test_reads_existing_preferences_and_preserves_metadata(self):
        root, patches = self._isolated_paths()
        with patches[0], patches[1], patches[2], patches[3]:
            write_json_atomic(
                root / "voice_preferences.json",
                {"assistant_address_user": "chefe", "assistant_style": "natural"},
                indent=2,
            )
            write_json_atomic(
                root / "operational_memory.json",
                {"updated_at": 1780000000.0, "preferences": ["Prefere respostas curtas em contexto operacional."], "notes": []},
                indent=2,
            )

            view = deep_memory.load_deep_memory(include_domain_sources=False)

        preferences = view["sections"][deep_memory.SECTION_PREFERENCES]
        self.assertTrue(any("Forma de tratamento" in item["texto"] for item in preferences))
        item = next(item for item in preferences if "Forma de tratamento" in item["texto"])
        self.assertEqual(item["metadados"]["origem"], "memory/voice_preferences.json")
        self.assertEqual(item["metadados"]["escopo"], "operacional")
        self.assertIn("desfazer", item["metadados"])
        self.assertGreaterEqual(item["metadados"]["confianca"], 0.8)

    def test_domain_query_finds_training_adaptive_rule(self):
        root, patches = self._isolated_paths()
        with patches[0], patches[1], patches[2], patches[3], patch.object(adaptive_preferences, "remember_operational_preference"):
            adaptive_preferences.remember_adaptive_suppression(
                "nao quero que voce me avise sobre treino",
                now=datetime(2026, 7, 24, 10, 0),
            )

            view = deep_memory.load_deep_memory(include_domain_sources=False)
            results = deep_memory.query_deep_memory_by_domain("treino", view=view)

        self.assertTrue(results)
        self.assertTrue(any(item["secao"] == deep_memory.SECTION_ADAPTIVE_RULES for item in results))
        self.assertTrue(any("evitar avisar treino" in item["texto"] for item in results))

    def test_explain_influence_for_training_notification_question(self):
        root, patches = self._isolated_paths()
        with patches[0], patches[1], patches[2], patches[3], patch.object(adaptive_preferences, "remember_operational_preference"):
            adaptive_preferences.remember_adaptive_suppression(
                "nao me avise sobre treino",
                now=datetime(2026, 7, 24, 10, 0),
            )
            view = deep_memory.load_deep_memory(include_domain_sources=False)

            explanation = deep_memory.explain_memory_influence("por que voce nao me avisou do treino?", view=view)

        self.assertEqual(explanation["domain"], "treino")
        self.assertTrue(explanation["items"])
        top = explanation["items"][0]
        self.assertEqual(top["metadados"]["origem"], "memory/adaptive_preferences.json")
        self.assertIn("nao me avise sobre treino", top["metadados"]["motivo"])

    def test_signals_conflict_instead_of_silent_choice(self):
        root, patches = self._isolated_paths()
        with patches[0], patches[1], patches[2], patches[3], patch.object(adaptive_preferences, "remember_operational_preference"):
            write_json_atomic(root / "voice_preferences.json", {"startup_briefing_enabled": True}, indent=2)
            adaptive_preferences.remember_adaptive_suppression(
                "para nao fazer o briefing amanha",
                now=datetime(2026, 7, 24, 10, 0),
            )

            view = deep_memory.load_deep_memory(include_domain_sources=False)

        self.assertTrue(view["conflicts"])
        self.assertEqual(view["conflicts"][0]["dominio"], "rotina")

    def test_formats_short_consultable_summary(self):
        root, patches = self._isolated_paths()
        with patches[0], patches[1], patches[2], patches[3], patch.object(adaptive_preferences, "remember_operational_preference"):
            write_json_atomic(root / "voice_preferences.json", {"assistant_address_user": "chefe"}, indent=2)
            adaptive_preferences.remember_adaptive_suppression(
                "nao quero que voce me avise sobre treino",
                now=datetime(2026, 7, 24, 10, 0),
            )

            summary = deep_memory.format_deep_memory_summary("preferencias e treino", limit=3)

        self.assertIn("Memoria profunda relevante:", summary)
        self.assertIn("origem", summary)
        self.assertLess(len(summary), 900)


if __name__ == "__main__":
    unittest.main()
