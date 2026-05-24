import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core.voice_command_suggestions import (
    command_correction_text,
    is_unclear_response,
    maybe_normalize_voice_command,
    maybe_suggest_probable_command,
)


def unclear_route(_text):
    return {"intent": "respond", "target": None, "response": "Nao entendi."}


def action_route(_text):
    return {"intent": "open_app", "target": {"app": "chrome"}}


class VoiceCommandSuggestionTests(unittest.TestCase):
    def test_text_mode_does_not_normalize(self):
        result = maybe_normalize_voice_command(
            "pesquisa notebook",
            False,
            apply_correction=lambda _text: "pesquisar notebook",
            route_command=unclear_route,
        )

        self.assertEqual(result, "pesquisa notebook")

    def test_learned_correction_wins_in_voice_mode(self):
        result = maybe_normalize_voice_command(
            "chegar chrome",
            True,
            apply_correction=lambda _text: "fechar chrome",
            route_command=unclear_route,
        )

        self.assertEqual(result, "fechar chrome")

    def test_contextual_followup_is_preserved(self):
        result = maybe_normalize_voice_command(
            "o que voce acha disso",
            True,
            apply_correction=lambda _text: "",
            route_command=unclear_route,
        )

        self.assertEqual(result, "o que voce acha disso")

    @patch("core.voice_command_suggestions.normalize_voice_command", return_value="pesquisar notebook")
    def test_unclear_voice_command_uses_normalized_candidate(self, _normalize_voice_command):
        result = maybe_normalize_voice_command(
            "pesquisa nutbook",
            True,
            apply_correction=lambda _text: "",
            route_command=unclear_route,
        )

        self.assertEqual(result, "pesquisar notebook")

    @patch("core.voice_command_suggestions.normalize_voice_command", return_value="fechar chrome")
    def test_known_routed_action_keeps_original_text(self, _normalize_voice_command):
        result = maybe_normalize_voice_command(
            "fechar chrome",
            True,
            apply_correction=lambda _text: "",
            route_command=action_route,
        )

        self.assertEqual(result, "fechar chrome")

    def test_probable_marketplace_query_corrects_common_noise(self):
        result = maybe_suggest_probable_command("mercado livre nutbook")

        self.assertEqual(result["action"]["intent"], "browser_search_site")
        self.assertEqual(result["action"]["target"]["query"], "notebook")
        self.assertIn("Mercado Livre", result["question"])

    def test_probable_youtube_query(self):
        result = maybe_suggest_probable_command("youtube lo fi foco")

        self.assertEqual(result["action"]["target"]["site"], "https://www.youtube.com")
        self.assertEqual(result["action"]["target"]["query"], "lo fi foco")

    def test_probable_spotify_song(self):
        result = maybe_suggest_probable_command("spotify filho mil")

        self.assertEqual(result["action"], {"intent": "browser_search_music", "target": {"service": "spotify", "query": "filho meu"}})

    def test_command_correction_text_for_known_actions(self):
        command = SimpleNamespace(
            action="browser_search_site",
            params={"query": "cadeira", "site": "https://www.mercadolivre.com.br"},
        )

        self.assertEqual(command_correction_text(command), "pesquisar cadeira no Mercado Livre")

    def test_command_correction_text_for_music_session(self):
        command = SimpleNamespace(action="browser_music_session", params={"vibe": "classico"})

        self.assertEqual(command_correction_text(command), "tocar música clássica")

    def test_unclear_response_detection(self):
        self.assertTrue(is_unclear_response({"intent": "respond", "response": "Pode repetir?"}))
        self.assertTrue(is_unclear_response({"intent": "respond", "response": "Qual site devo abrir?"}))
        self.assertFalse(is_unclear_response({"intent": "respond", "response": "Tudo certo."}))
        self.assertFalse(is_unclear_response({"intent": "open_app", "target": {"app": "chrome"}}))


if __name__ == "__main__":
    unittest.main()
