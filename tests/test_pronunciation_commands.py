import unittest
from unittest.mock import patch

from core.pronunciation_commands import list_pronunciation_response, maybe_handle_pronunciation_command


class PronunciationCommandTests(unittest.TestCase):
    def test_save_pronunciation(self):
        with patch("core.pronunciation_commands.set_tts_pronunciation") as save:
            result = maybe_handle_pronunciation_command("pronuncia de Codex como Codécs")

        self.assertEqual(result, "Pronuncia salva para Codex.")
        save.assert_called_once_with("Codex", "Codécs")

    def test_remove_existing_pronunciation(self):
        with patch("core.pronunciation_commands.remove_tts_pronunciation", return_value=True) as remove:
            result = maybe_handle_pronunciation_command("remover pronuncia de Codex")

        self.assertEqual(result, "Pronuncia removida para Codex.")
        remove.assert_called_once_with("Codex")

    def test_query_existing_pronunciation(self):
        with patch("core.pronunciation_commands.get_tts_pronunciation", return_value="Codécs"):
            result = maybe_handle_pronunciation_command("qual a pronuncia de Codex")

        self.assertEqual(result, "A pronuncia salva para Codex e Codécs.")

    def test_query_missing_pronunciation(self):
        with patch("core.pronunciation_commands.get_tts_pronunciation", return_value=None):
            result = maybe_handle_pronunciation_command("como voce fala Axel")

        self.assertEqual(result, "Ainda nao ha pronuncia personalizada para Axel.")

    def test_list_pronunciations_sorted_and_limited(self):
        with patch(
            "core.pronunciation_commands.load_tts_pronunciations",
            return_value={"Zeta": "zêta", "Axel": "áksel"},
        ):
            result = list_pronunciation_response()

        self.assertEqual(result, "Pronuncias salvas: Axel -> áksel; Zeta -> zêta.")

    def test_unknown_command_returns_none(self):
        self.assertIsNone(maybe_handle_pronunciation_command("abrir painel"))


if __name__ == "__main__":
    unittest.main()
