import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from core.conversation_reply import conversation_reply


class ConversationReplyTests(unittest.TestCase):
    def test_empty_reply_is_presence_ack(self):
        self.assertEqual(conversation_reply("", lambda _text: ""), "Estou aqui.")

    def test_microphone_test_reply_is_local(self):
        self.assertEqual(
            conversation_reply("um dois testando", lambda _text: self.fail("chat should not run")),
            "Teste de microfone recebido. Estou te ouvindo.",
        )

    def test_short_ack_reply_is_local(self):
        self.assertEqual(conversation_reply("isso", lambda _text: ""), "Peguei.")

    def test_greeting_uses_chat_then_fallback(self):
        self.assertEqual(conversation_reply("bom dia", lambda _text: "Bom dia, chefe."), "Bom dia, chefe.")
        self.assertEqual(conversation_reply("boa noite", lambda _text: ""), "Boa noite.")

    def test_name_question_tolerates_transcription_noise(self):
        self.assertEqual(conversation_reply("qual seu nome", lambda _text: ""), "Meu nome é Axel.")

    def test_introduction_is_local_in_conversation_mode(self):
        with TemporaryDirectory() as temp_dir, patch(
            "memory.assistant_customization.CUSTOMIZATION_PATH",
            Path(temp_dir) / "assistant_customization.json",
        ):
            response = conversation_reply("se apresente", lambda _text: self.fail("chat should not run"))
            self.assertIn("Prazer, eu sou o Axel", response)
            self.assertIn("Axel, o que temos para hoje?", response)
            self.assertNotIn("instagramavel", response)

    def test_identity_questions_are_local(self):
        self.assertIn("nasci ontem", conversation_reply("quantos anos voce tem", lambda _text: ""))
        self.assertIn("não chamaria isso de consciência", conversation_reply("voce sente algo", lambda _text: ""))

    def test_falls_back_to_chat_or_unclear_message(self):
        self.assertEqual(conversation_reply("conte uma ideia", lambda _text: "Ideia boa."), "Ideia boa.")
        self.assertEqual(
            conversation_reply("frase sem caminho util", lambda _text: ""),
            "Acho que eu ouvi meio torto. Repete de outro jeito?",
        )

    def test_conversation_mode_uses_useful_fallback_when_chat_fails(self):
        response = conversation_reply("ideia de presente para minha namorada", lambda _text: "")

        self.assertIn("presente", response)
        self.assertIn("carta curta", response)
        self.assertNotIn("ouvi meio torto", response)

    def test_conversation_mode_prefers_useful_fallback_over_weak_chat(self):
        response = conversation_reply(
            "pode me ajudar a aprender inglês?",
            lambda _text: "Não vou inventar sobre aprender inglês sem uma resposta confiável do chat local.",
        )

        self.assertIn("inglês", response)
        self.assertIn("misturar português e inglês", response)
        self.assertNotIn("Não vou inventar", response)

    def test_conversation_mode_uses_practical_fallback_when_chat_fails(self):
        response = conversation_reply("qual a receita de bolo de cenoura?", lambda _text: "")

        self.assertIn("bolo de cenoura", response)
        self.assertIn("forno médio", response)
        self.assertNotIn("ouvi meio torto", response)

    @patch("core.router_conversation.load_current_topic", return_value={"topic": "redes de computadores"})
    def test_conversation_mode_uses_current_topic_for_followup_when_chat_fails(self, _topic):
        response = conversation_reply("me da exemplos", lambda _text: "")

        self.assertIn("redes de computadores", response)
        self.assertIn("exercícios", response)

    @patch("core.router_conversation.update_current_topic_from_conversation")
    def test_conversation_mode_remembers_useful_local_fallback(self, update_topic):
        response = conversation_reply("me ajuda a estudar redes", lambda _text: "")

        self.assertIn("perguntas de fixação", response)
        update_topic.assert_called()


if __name__ == "__main__":
    unittest.main()
