import unittest
from unittest.mock import Mock, patch

from core.voice_profile_commands import maybe_handle_voice_profile_command, voice_profile_from_text


class VoiceProfileCommandTests(unittest.TestCase):
    def test_voice_profile_alias_prefers_longer_match(self):
        self.assertEqual(voice_profile_from_text("usar voz jarvis firme"), "jarvis-firme")

    def test_list_profiles(self):
        with patch("core.voice_profile_commands.list_voice_profiles", return_value=["jarvis", "natural"]):
            result = maybe_handle_voice_profile_command("listar vozes", {}, Mock())

        self.assertEqual(result, "Perfis de voz: jarvis, natural.")

    def test_voice_test_uses_saved_greeting(self):
        result = maybe_handle_voice_profile_command(
            "teste de voz",
            {"startup_voice_greeting": "Sistemas online."},
            Mock(),
        )

        self.assertEqual(result, "Sistemas online.")

    def test_apply_voice_profile_refreshes_preferences(self):
        preferences = {"startup_voice_greeting": "Pronto."}
        refresh = Mock()
        with patch("core.voice_profile_commands.apply_voice_profile", return_value=(True, "Perfil de voz aplicado: jarvis.")) as apply:
            result = maybe_handle_voice_profile_command("voz jarvis", preferences, refresh)

        self.assertEqual(result, "Perfil de voz aplicado: jarvis. Pronto.")
        apply.assert_called_once_with("jarvis")
        refresh.assert_called_once_with()

    def test_unknown_voice_profile_reports_hint(self):
        result = maybe_handle_voice_profile_command("voz espacial", {}, Mock())

        self.assertEqual(result, "Nao identifiquei o perfil de voz. Diga, por exemplo, voz jarvis firme ou voz natural.")

    def test_unrelated_command_returns_none(self):
        self.assertIsNone(maybe_handle_voice_profile_command("abrir painel", {}, Mock()))


if __name__ == "__main__":
    unittest.main()
