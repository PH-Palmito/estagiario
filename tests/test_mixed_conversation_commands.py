import unittest
from unittest.mock import patch

from core.router import route


class MixedConversationCommandTests(unittest.TestCase):
    def test_music_command_wins_when_sentence_has_conversation_tail(self):
        result = route("toca rock e depois me da uma dica de treino")

        self.assertEqual(result["intent"], "browser_music_session")
        self.assertEqual(result["target"]["vibe"], "rock")

    def test_music_command_keeps_useful_activity_tail_out_of_query(self):
        result = route("coloca musica para eu estudar")

        self.assertEqual(result["intent"], "browser_music_session")
        self.assertEqual(result["target"]["vibe"], "foco")

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_music_advice_without_play_verb_stays_conversation(self, _chat):
        result = route("me da uma dica de musica para estudar")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("conversa útil", result["response"])

    def test_open_site_wins_when_sentence_has_conversation_tail(self):
        result = route("abre youtube e depois me da uma dica de treino")

        self.assertEqual(result["intent"], "open_url")
        self.assertEqual(result["target"], "https://www.youtube.com")

    def test_focus_app_wins_when_sentence_has_conversation_tail(self):
        result = route("foca no chrome e depois me explica isso")

        self.assertEqual(result["intent"], "focus_app")
        self.assertEqual(result["target"], "chrome")

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_open_ended_business_idea_does_not_become_open_command(self, _chat):
        result = route("ideia de abrir um negocio pequeno")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("conversa útil", result["response"])

    def test_reminder_command_keeps_conversation_tail_out_of_target(self):
        result = route("me lembre de comprar presente amanha e depois me da ideias")

        self.assertEqual(result["intent"], "reminder_add")
        self.assertEqual(result["target"], "comprar presente amanha")

    def test_agenda_command_keeps_conversation_tail_out_of_target(self):
        result = route("adicionar na agenda revisar redes hoje e depois toca musica")

        self.assertEqual(result["intent"], "agenda_add")
        self.assertEqual(result["target"], "revisar redes hoje")

    def test_marketplace_search_keeps_conversation_tail_out_of_query(self):
        result = route("pesquise notebook no mercado livre e depois me da uma dica")

        self.assertEqual(result["intent"], "browser_search_site")
        self.assertEqual(result["target"]["site"], "https://www.mercadolivre.com.br")
        self.assertEqual(result["target"]["query"], "notebook")

    def test_youtube_search_keeps_conversation_tail_out_of_query(self):
        result = route("pesquise redes de computadores no youtube e depois resuma")

        self.assertEqual(result["intent"], "browser_search_site")
        self.assertEqual(result["target"]["site"], "https://www.youtube.com")
        self.assertEqual(result["target"]["query"], "redes computadores")

    def test_trailing_music_command_wins_after_conversation_intro(self):
        result = route("me explica redes e toca musica para estudar")

        self.assertEqual(result["intent"], "browser_music_session")
        self.assertEqual(result["target"]["vibe"], "foco")

    def test_trailing_open_site_command_wins_after_conversation_intro(self):
        result = route("me fala uma dica de estudo e abre youtube")

        self.assertEqual(result["intent"], "open_url")
        self.assertEqual(result["target"], "https://www.youtube.com")

    def test_trailing_reminder_command_wins_after_conversation_intro(self):
        result = route("me explica redes e depois me lembre de revisar redes amanha")

        self.assertEqual(result["intent"], "reminder_add")
        self.assertEqual(result["target"], "revisar redes amanha")

    def test_trailing_youtube_search_wins_after_conversation_intro(self):
        result = route("me explica redes e pesquise tcp no youtube")

        self.assertEqual(result["intent"], "browser_search_site")
        self.assertEqual(result["target"]["site"], "https://www.youtube.com")
        self.assertEqual(result["target"]["query"], "tcp")

    def test_trailing_marketplace_search_wins_after_conversation_intro(self):
        result = route("me ajuda a escolher e depois pesquise notebook no mercado livre")

        self.assertEqual(result["intent"], "browser_search_site")
        self.assertEqual(result["target"]["site"], "https://www.mercadolivre.com.br")
        self.assertEqual(result["target"]["query"], "notebook")


if __name__ == "__main__":
    unittest.main()
