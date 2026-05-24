import unittest
from unittest.mock import Mock, patch

from core.humor_commands import current_humor_description, humor_test_response, maybe_handle_humor_command


class HumorCommandTests(unittest.TestCase):
    def test_current_humor_description_for_enabled_style(self):
        preferences = {
            "assistant_humor_enabled": True,
            "assistant_humor_style": "filosofico",
            "assistant_humor_level": 2,
        }

        self.assertEqual(current_humor_description(preferences), "Humor atual: reflexivo, intensidade 2 de 3.")

    def test_humor_test_neutral(self):
        preferences = {
            "assistant_humor_enabled": False,
            "assistant_humor_style": "neutro",
            "assistant_humor_level": 0,
        }

        self.assertEqual(
            humor_test_response(preferences),
            "Teste de humor: sistemas online. Direto, funcional e sem piada lateral. So trabalho.",
        )

    def test_set_humor_style_updates_preferences_and_refreshes(self):
        preferences = {
            "assistant_humor_enabled": True,
            "assistant_humor_style": "seco",
            "assistant_humor_level": 1,
        }
        refresh = Mock()
        with patch("core.humor_commands.update_voice_preferences") as update:
            result = maybe_handle_humor_command("humor jarvis", preferences, refresh)

        self.assertEqual(result, "Humor atual: jarvis, intensidade 2 de 3.")
        update.assert_called_once_with(
            {
                "assistant_humor_enabled": True,
                "assistant_humor_style": "jarvis",
                "assistant_humor_level": 2,
            }
        )
        refresh.assert_called_once_with()

    def test_neutral_humor_disables_and_zeroes_level(self):
        preferences = {
            "assistant_humor_enabled": True,
            "assistant_humor_style": "jarvis",
            "assistant_humor_level": 3,
        }
        with patch("core.humor_commands.update_voice_preferences"):
            result = maybe_handle_humor_command("sem humor", preferences, Mock())

        self.assertEqual(result, "Humor atual: neutro, intensidade zero.")
        self.assertEqual(preferences["assistant_humor_enabled"], False)
        self.assertEqual(preferences["assistant_humor_level"], 0)

    def test_unknown_humor_command_suggests_options(self):
        result = maybe_handle_humor_command("humor espacial", {}, Mock())

        self.assertEqual(
            result,
            "Nao identifiquei o humor. Tente: humor jarvis, humor seco, humor reflexivo, humor leve ou humor neutro.",
        )

    def test_unrelated_command_returns_none(self):
        self.assertIsNone(maybe_handle_humor_command("abrir treino", {}, Mock()))


if __name__ == "__main__":
    unittest.main()
