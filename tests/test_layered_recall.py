import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.memory_commands import maybe_handle_long_memory_command
from memory import curated_memory, layered_recall, long_memory, session_index


class LayeredRecallTests(unittest.TestCase):
    def _patch_memory_paths(self, temp_dir: str):
        root = Path(temp_dir)
        return (
            patch.object(curated_memory, "MEMORY_DIR", root),
            patch.object(curated_memory, "CORE_MEMORY_PATH", root / "core_memory.md"),
            patch.object(curated_memory, "USER_PROFILE_PATH", root / "user_profile.md"),
            patch.object(long_memory, "LONG_MEMORY_PATH", root / "long_memory.json"),
            patch.object(session_index, "SESSION_INDEX_PATH", root / "session_index.sqlite3"),
        )

    def test_layered_recall_combines_curated_long_memory_and_sessions(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            patches = self._patch_memory_paths(temp_dir)
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                curated_memory.ensure_curated_memory_files()
                curated_memory.CORE_MEMORY_PATH.write_text("# Core\n- Axel usa AxelBrain.\n", encoding="utf-8")
                curated_memory.USER_PROFILE_PATH.write_text("# User\n- Prefere respostas curtas.\n", encoding="utf-8")
                long_memory.remember_fact("Decidimos priorizar AxelBrain e agentes especialistas.", category="decision")
                session_index.index_exchange(
                    "falamos sobre agentes especialistas do Axel",
                    "AxelBrain escolhe agente, toolset e risco.",
                    session_id="unit-session",
                )

                recall = layered_recall.layered_memory_recall("AxelBrain agentes", include_transcript=True)

        self.assertTrue(recall["curated"])
        self.assertTrue(recall["semantic"])
        self.assertTrue(recall["expanded_summary"])
        self.assertTrue(recall["transcript"])

    def test_format_layered_recall_includes_transcript_when_requested(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            patches = self._patch_memory_paths(temp_dir)
            with patches[0], patches[1], patches[2], patches[3], patches[4]:
                curated_memory.ensure_curated_memory_files()
                session_index.index_exchange(
                    "criamos memoria em camadas",
                    "Ela busca resumo e transcript original.",
                    session_id="unit-session",
                )

                text = layered_recall.format_layered_memory_recall("memoria camadas", include_transcript=True)

        self.assertIn("Recall em camadas", text)
        self.assertIn("Transcript original", text)

    def test_memory_command_uses_layered_recall(self):
        with patch("core.memory_commands.format_layered_memory_recall", return_value="Recall em camadas para Axel."):
            result = maybe_handle_long_memory_command("recall em camadas sobre Axel")

        self.assertEqual(result, "Recall em camadas para Axel.")


if __name__ == "__main__":
    unittest.main()
