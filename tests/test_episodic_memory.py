import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.memory_commands import maybe_handle_long_memory_command
from memory import episodic_memory, operational_context


class EpisodicMemoryTests(unittest.TestCase):
    def test_build_episode_summary_extracts_points_actions_and_models(self):
        turns = [
            {"role": "user", "text": "vamos fazer memoria episodica no Axel", "source": "test"},
            {"role": "assistant", "text": "Vou criar um resumo por sessao.", "source": "test"},
        ]
        events = [
            {
                "event": "command_execute_end",
                "data": {
                    "action": "file_write",
                    "risk_level": "critical",
                    "action_class": "sensitive_write",
                    "duration_ms": 1200,
                    "success": False,
                    "error": "negado",
                },
            },
            {
                "event": "model_call_end",
                "data": {
                    "provider": "cloud",
                    "model": "gemini",
                    "fallback_used": True,
                    "success": True,
                    "total_tokens_estimate": 500,
                },
            },
        ]

        episode = episodic_memory.build_episode_summary(
            session_id="unit",
            turns=turns,
            events=events,
            now=1_779_000_000,
        )

        self.assertEqual(episode["session_id"], "unit")
        self.assertIn("memoria episodica", episode["important_points"][0])
        self.assertEqual(episode["action_errors"][0]["action"], "file_write")
        self.assertEqual(episode["model"]["fallback_count"], 1)
        self.assertEqual(episode["model"]["tokens_estimate"], 500)

    def test_save_latest_and_search_episode(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "episodes.json"
            episode = episodic_memory.build_episode_summary(
                session_id="unit",
                turns=[{"role": "user", "text": "prioridade e AxelBrain", "source": "test"}],
                events=[],
                now=1_779_000_000,
            )

            saved = episodic_memory.save_episode_summary(episode, path=path)
            latest = episodic_memory.latest_episode(path=path)
            matches = episodic_memory.search_episodes("AxelBrain", path=path)

        self.assertEqual(saved["id"], latest["id"])
        self.assertEqual(matches[0]["id"], saved["id"])

    def test_format_episode_handles_empty_memory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "episodes.json"
            with patch.object(episodic_memory, "EPISODES_PATH", path):
                text = episodic_memory.format_episode()

        self.assertIn("Ainda nao ha", text)

    def test_memory_commands_save_show_list_and_search_episodes(self):
        with (
            patch("core.memory_commands.build_episode_summary", return_value={"id": "ep", "date": "2026-05-30", "summary": "Resumo."}),
            patch("core.memory_commands.save_episode_summary", return_value={"id": "ep", "date": "2026-05-30", "summary": "Resumo."}),
            patch("core.memory_commands.format_episode", return_value="Episodio 2026-05-30: Resumo."),
        ):
            saved = maybe_handle_long_memory_command("salvar memoria episodica")

        with patch("core.memory_commands.format_episode", return_value="Episodio 2026-05-30: Resumo."):
            shown = maybe_handle_long_memory_command("memoria episodica")
        with patch("core.memory_commands.format_episode_list", return_value="Episodios recentes: 1. Resumo."):
            listed = maybe_handle_long_memory_command("listar episodios")
        with patch("core.memory_commands.format_episode_search", return_value="Episodios encontrados: Resumo."):
            found = maybe_handle_long_memory_command("buscar na memoria episodica sobre AxelBrain")

        self.assertIn("Memoria episodica atualizada", saved)
        self.assertEqual(shown, "Episodio 2026-05-30: Resumo.")
        self.assertEqual(listed, "Episodios recentes: 1. Resumo.")
        self.assertEqual(found, "Episodios encontrados: Resumo.")

    def test_operational_context_compacts_latest_episode(self):
        with patch.object(operational_context, "_load_json", return_value={}):
            with patch("memory.episodic_memory.latest_episode", return_value={
                "date": "2026-05-30",
                "summary": "Pontos principais: memoria episodica.",
                "important_points": ["memoria episodica"],
                "next_steps": ["continuar"],
            }):
                episode = operational_context._load_latest_episode()

        self.assertEqual(episode["date"], "2026-05-30")
        self.assertIn("memoria episodica", episode["summary"])


if __name__ == "__main__":
    unittest.main()
