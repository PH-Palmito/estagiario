import unittest
from unittest.mock import patch

from services.whatsapp_gateway import handle_whatsapp_text
from tools.whatsapp_tools import simulate_whatsapp_message


class WhatsAppLocalConversationTests(unittest.TestCase):
    def test_local_conversation_smoke(self):
        result = simulate_whatsapp_message("status do whatsapp", sender="5571988393851")

        self.assertIn("Resposta WhatsApp:", result)
        self.assertIn("Ponte WhatsApp local", result)

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_whatsapp_open_conversation_uses_useful_fallback(self, _chat):
        result = handle_whatsapp_text("ideia de presente para minha namorada")

        self.assertTrue(result.ok)
        self.assertEqual(result.action, "respond")
        self.assertIn("presente", result.text)
        self.assertNotIn("Não vou inventar", result.text)

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_whatsapp_practical_question_uses_practical_fallback(self, _chat):
        result = handle_whatsapp_text("qual a receita de bolo de cenoura?")

        self.assertTrue(result.ok)
        self.assertEqual(result.action, "respond")
        self.assertIn("bolo de cenoura", result.text)
        self.assertNotIn("Não vou inventar", result.text)

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_whatsapp_learning_conversation_uses_useful_fallback(self, _chat):
        result = handle_whatsapp_text("me ajuda a estudar redes")

        self.assertTrue(result.ok)
        self.assertEqual(result.action, "respond")
        self.assertIn("perguntas de fixação", result.text)
        self.assertNotIn("Não vou inventar", result.text)

    def test_whatsapp_mixed_conversation_search_routes_to_action(self):
        result = handle_whatsapp_text("me explica redes e pesquise tcp no youtube")

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "blocked")
        self.assertIn("bloqueado", result.text)


if __name__ == "__main__":
    unittest.main()
