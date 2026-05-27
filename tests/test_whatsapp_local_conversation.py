import unittest

from tools.whatsapp_tools import simulate_whatsapp_message


class WhatsAppLocalConversationTests(unittest.TestCase):
    def test_local_conversation_smoke(self):
        result = simulate_whatsapp_message("status do whatsapp", sender="5571988393851")

        self.assertIn("Resposta WhatsApp:", result)
        self.assertIn("Ponte WhatsApp local", result)


if __name__ == "__main__":
    unittest.main()
