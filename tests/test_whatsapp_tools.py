import unittest
from unittest.mock import patch

from tools import whatsapp_tools


class WhatsAppToolsTests(unittest.TestCase):
    def test_status_mentions_endpoint_and_allowlist(self):
        with patch.object(whatsapp_tools, "WHATSAPP_ALLOWED_SENDERS", "5571999990000"):
            result = whatsapp_tools.whatsapp_bridge_status()

        self.assertIn("Ponte WhatsApp local", result)
        self.assertIn("1 numero", result)

    def test_simulate_message_uses_allowed_sender(self):
        with (
            patch.object(whatsapp_tools, "WHATSAPP_ALLOWED_SENDERS", "5571999990000"),
            patch.object(whatsapp_tools, "handle_whatsapp_payload") as handle,
        ):
            handle.return_value = type("Response", (), {"ok": True, "text": "Briefing"})()
            result = whatsapp_tools.simulate_whatsapp_message("briefing")

        self.assertEqual(result, "Resposta WhatsApp: Briefing")
        handle.assert_called_once()
        self.assertEqual(handle.call_args.args[0]["from"], "5571999990000")


if __name__ == "__main__":
    unittest.main()
