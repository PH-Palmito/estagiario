import unittest
from unittest.mock import Mock, patch

from services import telegram_gateway as gateway


class TelegramGatewayTests(unittest.TestCase):
    def setUp(self):
        gateway._CHAT_CONTEXT.clear()

    def test_parse_allowed_chat_ids(self):
        self.assertEqual(gateway.parse_allowed_chat_ids("123, 456;789"), {"123", "456", "789"})

    def test_blocks_unknown_chat(self):
        result = gateway.handle_telegram_update(
            {"message": {"chat": {"id": 123}, "text": "briefing"}},
            allowed_chat_ids={"456"},
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "blocked")

    def test_direct_response_returns_text_with_contract(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "respond", "response": "Oi."},
            intent_level="conversa",
            group_name="conversation",
            detector_name="detect_test",
        )
        fake_trace.checked_detectors = 1
        fake_trace.checked_groups = ["conversation"]
        with patch.object(gateway, "route_trace", return_value=fake_trace):
            result = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "oi"}},
                allowed_chat_ids={"123"},
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "Oi.")
        self.assertEqual(result.contract["channel"], "remote")

    def test_allows_read_command(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "daily_briefing", "target": None},
            intent_level="pergunta",
            group_name="daily",
            detector_name="detect_briefing",
        )
        fake_trace.checked_detectors = 2
        fake_trace.checked_groups = ["daily"]
        with (
            patch.object(gateway, "route_trace", return_value=fake_trace),
            patch.object(gateway, "execute_telegram_command", return_value="Briefing do dia"),
        ):
            result = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "briefing"}},
                allowed_chat_ids={"123"},
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "Briefing do dia")
        self.assertEqual(result.action, "daily_briefing")
        self.assertTrue(result.contract["remote_policy"]["can_execute"])

    def test_blocks_write_command_even_from_allowed_chat(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "agenda_add", "target": "hoje teste"},
            intent_level="comando_direto",
            group_name="daily",
            detector_name="detect_agenda_add",
        )
        fake_trace.checked_detectors = 3
        fake_trace.checked_groups = ["daily"]
        with patch.object(gateway, "route_trace", return_value=fake_trace):
            result = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "adicionar na agenda hoje teste"}},
                allowed_chat_ids={"123"},
            )

        self.assertFalse(result.ok)
        self.assertIn("confirmacao no PC", result.text)
        self.assertFalse(result.contract["remote_policy"]["can_execute"])

    def test_confirmation_help_after_pending_remote_action_is_explicit(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "media_play_target", "target": "back in black"},
            intent_level="comando_direto",
            group_name="music",
            detector_name="detect_music",
        )
        fake_trace.checked_detectors = 5
        fake_trace.checked_groups = ["music"]
        with patch.object(gateway, "route_trace", return_value=fake_trace):
            blocked = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "pode tocar back in black?"}},
                allowed_chat_ids={"123"},
            )

        help_response = gateway.handle_telegram_update(
            {"message": {"chat": {"id": 123}, "text": "como eu confirmo?"}},
            allowed_chat_ids={"123"},
        )

        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.status, "confirmation_required")
        self.assertTrue(help_response.ok)
        self.assertIn("Confirmar acao remota", help_response.text)
        self.assertIn("confirmar/cancelar", help_response.text)
        self.assertIn("inline_keyboard", help_response.reply_markup)

    def test_confirm_executes_pending_light_remote_action(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "media_play_target", "target": "back in black"},
            intent_level="comando_direto",
            group_name="music",
            detector_name="detect_music",
        )
        fake_trace.checked_detectors = 5
        fake_trace.checked_groups = ["music"]
        with (
            patch.object(gateway, "route_trace", return_value=fake_trace),
            patch.object(gateway, "execute_telegram_command", return_value="Tocando.") as execute_mock,
        ):
            pending = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "pode tocar back in black?"}},
                allowed_chat_ids={"123"},
            )
            confirmed = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "confirmar"}},
                allowed_chat_ids={"123"},
            )

        self.assertEqual(pending.status, "confirmation_required")
        self.assertTrue(confirmed.ok)
        self.assertEqual(confirmed.text, "Tocando.")
        self.assertEqual(execute_mock.call_count, 1)
        self.assertIn("inline_keyboard", pending.reply_markup)

    def test_confirm_executes_pending_music_search_action(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "browser_search_music", "target": {"service": "spotify", "query": "black in black"}},
            intent_level="comando_direto",
            group_name="music",
            detector_name="detect_music_command",
        )
        fake_trace.checked_detectors = 5
        fake_trace.checked_groups = ["music"]
        with (
            patch.object(gateway, "route_trace", return_value=fake_trace),
            patch.object(gateway, "execute_telegram_command", return_value="Tocando Black in Black.") as execute_mock,
        ):
            pending = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "Toca Black in black"}},
                allowed_chat_ids={"123"},
            )
            confirmed = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "confirmar"}},
                allowed_chat_ids={"123"},
            )

        self.assertEqual(pending.status, "confirmation_required")
        self.assertIn("browser_search_music", pending.text)
        self.assertTrue(confirmed.ok)
        self.assertEqual(confirmed.text, "Tocando Black in Black.")
        self.assertEqual(execute_mock.call_count, 1)

    def test_callback_button_confirms_pending_action(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "browser_search_music", "target": {"service": "spotify", "query": "black in black"}},
            intent_level="comando_direto",
            group_name="music",
            detector_name="detect_music_command",
        )
        fake_trace.checked_detectors = 5
        fake_trace.checked_groups = ["music"]
        with (
            patch.object(gateway, "route_trace", return_value=fake_trace),
            patch.object(gateway, "execute_telegram_command", return_value="Tocando Black in Black.") as execute_mock,
        ):
            pending = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "Toca Black in black"}},
                allowed_chat_ids={"123"},
            )
            confirmed = gateway.handle_telegram_update(
                {
                    "callback_query": {
                        "id": "callback-1",
                        "data": "axel_confirm",
                        "from": {"id": 123, "first_name": "Php"},
                        "message": {"message_id": 2, "chat": {"id": 123}},
                    }
                },
                allowed_chat_ids={"123"},
            )

        self.assertEqual(pending.status, "confirmation_required")
        self.assertIn("inline_keyboard", pending.reply_markup)
        self.assertTrue(confirmed.ok)
        self.assertEqual(confirmed.callback_query_id, "callback-1")
        self.assertEqual(confirmed.text, "Tocando Black in Black.")
        self.assertEqual(execute_mock.call_count, 1)

    def test_remote_mode_activation_stays_disabled_for_app_actions(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "open_app", "target": "notepad"},
            intent_level="comando_direto",
            group_name="apps",
            detector_name="detect_open_app",
        )
        fake_trace.checked_detectors = 5
        fake_trace.checked_groups = ["apps"]
        with patch.object(gateway, "route_trace", return_value=fake_trace):
            blocked = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "abrir notepad"}},
                allowed_chat_ids={"123"},
            )
            enabled = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "ativar remoto por 30 minutos"}},
                allowed_chat_ids={"123"},
            )
            pending = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "abrir notepad"}},
                allowed_chat_ids={"123"},
            )

        self.assertEqual(blocked.status, "blocked")
        self.assertEqual(enabled.status, "remote_mode_disabled")
        self.assertFalse(enabled.ok)
        self.assertEqual(pending.status, "blocked")
        self.assertIsNone(pending.reply_markup)

    def test_retry_reuses_last_non_conversation_command(self):
        calls = []

        def fake_route_trace(text):
            calls.append(text)
            fake_trace = Mock()
            fake_trace.match = Mock(
                result={"intent": "investment_memory_answer", "target": text},
                intent_level="pergunta",
                group_name="investment_questions",
                detector_name="detect_investment_question_command",
            )
            fake_trace.checked_detectors = 4
            fake_trace.checked_groups = ["investment_questions"]
            return fake_trace

        with (
            patch.object(gateway, "route_trace", side_effect=fake_route_trace),
            patch.object(gateway, "execute_telegram_command", return_value="Sem noticia nova."),
        ):
            first = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "Tem noticias da carteira ?"}},
                allowed_chat_ids={"123"},
            )
            second = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "pode tentar novamente?"}},
                allowed_chat_ids={"123"},
            )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(calls, ["Tem noticias da carteira ?", "Tem noticias da carteira ?"])


if __name__ == "__main__":
    unittest.main()
