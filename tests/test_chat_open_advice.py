import unittest
from unittest.mock import patch

from llm import chat


class ChatOpenAdviceTests(unittest.TestCase):
    def test_open_advice_requests_are_complex_enough_for_stronger_model(self):
        examples = [
            "ideia de presente para minha namorada?",
            "dicas de treino em casa",
            "quero comer melhor sem fazer dieta",
            "pode me ajudar a estudar redes?",
            "quero aprender inglês misturando com português",
            "me ensina o básico de banco de dados",
        ]

        for phrase in examples:
            with self.subTest(phrase=phrase):
                self.assertTrue(chat._looks_like_complex_request(phrase))

    def test_small_talk_is_not_complex_by_default(self):
        examples = [
            "bom dia",
            "axel how are you?",
            "está aí?",
        ]

        for phrase in examples:
            with self.subTest(phrase=phrase):
                self.assertFalse(chat._looks_like_complex_request(phrase))

    @patch("llm.chat.index_exchange")
    @patch("llm.chat.update_current_topic_from_conversation")
    @patch("llm.chat.ask_model", return_value="Um bom presente combina utilidade e lembranca pessoal.")
    def test_chat_response_uses_cloud_for_open_advice_when_available(self, ask_model, _topic, _index):
        with patch.object(chat, "GEMINI_COMPLEX_CHAT_ENABLED", True), patch.object(chat, "NVIDIA_API_KEY", "nv-key"), patch.object(
            chat, "GEMINI_API_KEY", ""
        ), patch.dict(chat.PREFERENCES, {"ai_text_provider": "auto", "chat_enabled": True}, clear=False):
            response = chat.chat_response("ideia de presente para minha namorada?")

        self.assertIn("presente", response)
        self.assertEqual(ask_model.call_args.kwargs["provider"], "cloud")

    @patch("llm.chat.index_exchange")
    @patch("llm.chat.update_current_topic_from_conversation")
    @patch("llm.chat.ask_model", return_value="Comece por vocabulário curto e frases do seu dia.")
    def test_chat_response_uses_cloud_for_learning_when_available(self, ask_model, _topic, _index):
        with patch.object(chat, "GEMINI_COMPLEX_CHAT_ENABLED", True), patch.object(chat, "NVIDIA_API_KEY", "nv-key"), patch.object(
            chat, "GEMINI_API_KEY", ""
        ), patch.dict(chat.PREFERENCES, {"ai_text_provider": "auto", "chat_enabled": True}, clear=False):
            response = chat.chat_response("quero aprender inglês misturando com português")

        self.assertIn("vocabulário", response)
        self.assertEqual(ask_model.call_args.kwargs["provider"], "cloud")

    @patch("llm.chat.ask_model", return_value="Não vou inventar sem uma resposta confiável do chat local.")
    def test_chat_response_rejects_weak_model_answer(self, _ask_model):
        with patch.object(chat, "GEMINI_COMPLEX_CHAT_ENABLED", False), patch.dict(
            chat.PREFERENCES,
            {"ai_text_provider": "local", "chat_enabled": True},
            clear=False,
        ):
            response = chat.chat_response("pode me ajudar a aprender inglês?")

        self.assertIsNone(response)


if __name__ == "__main__":
    unittest.main()
