import unittest

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
        self.assertEqual(conversation_reply("qual seu nome", lambda _text: ""), "Meu nome e Estagiario.")

    def test_identity_questions_are_local(self):
        self.assertIn("nasci ontem", conversation_reply("quantos anos voce tem", lambda _text: ""))
        self.assertIn("nao chamaria isso de consciencia", conversation_reply("voce sente algo", lambda _text: ""))

    def test_falls_back_to_chat_or_unclear_message(self):
        self.assertEqual(conversation_reply("conte uma ideia", lambda _text: "Ideia boa."), "Ideia boa.")
        self.assertEqual(
            conversation_reply("conte uma ideia", lambda _text: ""),
            "Acho que eu ouvi meio torto. Repete de outro jeito?",
        )


if __name__ == "__main__":
    unittest.main()
