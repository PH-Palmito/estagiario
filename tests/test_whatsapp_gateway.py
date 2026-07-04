import unittest
from unittest.mock import patch

from services import whatsapp_gateway as gateway


class WhatsAppGatewayTests(unittest.TestCase):
    def test_parse_allowed_senders_normalizes_numbers(self):
        self.assertEqual(
            gateway.parse_allowed_senders("+55 71 99999-0000,55718888"),
            {"5571999990000", "55718888"},
        )

    def test_blocks_unknown_sender(self):
        result = gateway.handle_whatsapp_payload(
            {"from": "+55 71 99999-0000", "text": "briefing"},
            allowed_senders={"55718888"},
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "blocked")

    def test_allows_read_only_command(self):
        with (
            patch.object(gateway, "route_text", return_value={"intent": "daily_briefing", "target": None}),
            patch.object(gateway, "execute_whatsapp_command", return_value="Briefing do dia"),
        ):
            result = gateway.handle_whatsapp_payload(
                {"from": "+55 71 99999-0000", "text": "briefing"},
                allowed_senders={"5571999990000"},
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "Briefing do dia.")
        self.assertEqual(result.action, "daily_briefing")

    @patch.object(gateway, "maybe_handle_shared_command", return_value="Autoteste rápido do Axel: 13/13 rotas essenciais OK.")
    def test_shared_self_check_command_returns_without_routing_action(self, shared):
        with patch.object(gateway, "route_text") as route_text:
            result = gateway.handle_whatsapp_payload(
                {"from": "+55 71 99999-0000", "text": "/autoteste"},
                allowed_senders={"5571999990000"},
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.action, "shared_command")
        self.assertIn("13/13", result.text)
        self.assertEqual(shared.call_args.args, ("/autoteste",))
        route_text.assert_not_called()

    def test_read_only_response_is_polished(self):
        with (
            patch.object(gateway, "route_text", return_value={"intent": "daily_briefing", "target": None}),
            patch.object(gateway, "execute_whatsapp_command", return_value="Nao encontrei precos. O que voce quer"),
        ):
            result = gateway.handle_whatsapp_payload(
                {"from": "+55 71 99999-0000", "text": "briefing"},
                allowed_senders={"5571999990000"},
            )

        self.assertEqual(result.text, "Não encontrei preços. O que você quer.")

    def test_blocks_write_command_even_from_allowed_sender(self):
        with patch.object(gateway, "route_text", return_value={"intent": "agenda_add", "target": "hoje teste"}):
            result = gateway.handle_whatsapp_payload(
                {"from": "5571999990000", "text": "adicionar na agenda hoje teste"},
                allowed_senders={"5571999990000"},
            )

        self.assertFalse(result.ok)
        self.assertIn("bloqueado", result.text)
        self.assertIn("segurança", result.text)

    def test_direct_response_returns_text(self):
        with patch.object(gateway, "route_text", return_value={"intent": "respond", "response": "Oi."}):
            result = gateway.handle_whatsapp_payload(
                {"from": "5571999990000", "text": "oi"},
                allowed_senders={"5571999990000"},
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "Oi.")


if __name__ == "__main__":
    unittest.main()
