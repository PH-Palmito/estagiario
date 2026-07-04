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

    def test_direct_response_is_polished(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "respond", "response": "Nao encontrei precos claros. O que voce quer?"},
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

        self.assertEqual(result.text, "Não encontrei preços claros. O que você quer?")

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_open_conversation_uses_real_useful_fallback(self, _chat):
        result = gateway.handle_telegram_update(
            {"message": {"chat": {"id": 123}, "text": "ideia de presente para minha namorada"}},
            allowed_chat_ids={"123"},
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.action, "respond")
        self.assertIn("presente", result.text)
        self.assertNotIn("Não vou inventar", result.text)

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_practical_question_uses_real_practical_fallback(self, _chat):
        result = gateway.handle_telegram_update(
            {"message": {"chat": {"id": 123}, "text": "qual a receita de bolo de cenoura?"}},
            allowed_chat_ids={"123"},
        )

        self.assertTrue(result.ok)
        self.assertIn("bolo de cenoura", result.text)
        self.assertNotIn("Não vou inventar", result.text)

    @patch("core.router_conversation.chat_response", return_value=None)
    def test_learning_conversation_uses_real_useful_fallback(self, _chat):
        result = gateway.handle_telegram_update(
            {"message": {"chat": {"id": 123}, "text": "me ajuda a estudar redes"}},
            allowed_chat_ids={"123"},
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.action, "respond")
        self.assertIn("perguntas de fixação", result.text)
        self.assertNotIn("Não vou inventar", result.text)

    def test_mixed_conversation_search_routes_to_action_remotely(self):
        result = gateway.handle_telegram_update(
            {"message": {"chat": {"id": 123}, "text": "me explica redes e pesquise tcp no youtube"}},
            allowed_chat_ids={"123"},
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "blocked")
        self.assertEqual(result.contract["route"]["intent"], "browser_search_site")
        self.assertNotEqual(result.contract["route"]["intent"], "respond")

    def test_parse_voice_message_metadata(self):
        request = gateway.parse_inbound_update(
            {
                "message": {
                    "chat": {"id": 123},
                    "voice": {"file_id": "voice-1", "duration": 4, "mime_type": "audio/ogg"},
                }
            }
        )

        self.assertEqual(request.chat_id, "123")
        self.assertEqual(request.media_kind, "voice")
        self.assertEqual(request.media_file_id, "voice-1")
        self.assertEqual(request.media_duration, 4)
        self.assertEqual(request.media_mime_type, "audio/ogg")

    def test_voice_message_without_transcriber_is_explicit(self):
        result = gateway.handle_telegram_update(
            {"message": {"chat": {"id": 123}, "voice": {"file_id": "voice-1"}}},
            allowed_chat_ids={"123"},
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "audio_transcription_unavailable")
        self.assertIn("Recebi o áudio", result.text)

    def test_voice_message_transcription_reuses_text_flow(self):
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
            patch.object(gateway, "execute_telegram_command", return_value="Briefing remoto."),
        ):
            result = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "voice": {"file_id": "voice-1"}}},
                allowed_chat_ids={"123"},
                transcribe_audio=lambda request: "briefing",
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "Briefing remoto.")
        self.assertEqual(result.action, "daily_briefing")

    def test_voice_message_transcription_failure_is_reported(self):
        def boom(_request):
            raise RuntimeError("sem codec")

        result = gateway.handle_telegram_update(
            {"message": {"chat": {"id": 123}, "voice": {"file_id": "voice-1"}}},
            allowed_chat_ids={"123"},
            transcribe_audio=boom,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.status, "audio_transcription_failed")
        self.assertIn("sem codec", result.text)

    @patch.object(gateway, "maybe_handle_shared_command", return_value="Status do Axel: operacional.")
    def test_shared_status_command_returns_without_routing_action(self, shared):
        with patch.object(gateway, "route_trace") as route_trace:
            result = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "/status"}},
                allowed_chat_ids={"123"},
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "Status do Axel: operacional.")
        self.assertEqual(result.action, "shared_command")
        self.assertEqual(shared.call_args.args, ("/status",))
        self.assertIn("undo_last", shared.call_args.kwargs)
        route_trace.assert_not_called()

    @patch.object(gateway, "maybe_handle_shared_command", return_value="Autoteste rápido do Axel: 13/13 rotas essenciais OK.")
    def test_shared_self_check_command_returns_without_routing_action(self, shared):
        with patch.object(gateway, "route_trace") as route_trace:
            result = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "/autoteste"}},
                allowed_chat_ids={"123"},
            )

        self.assertTrue(result.ok)
        self.assertEqual(result.action, "shared_command")
        self.assertIn("13/13", result.text)
        self.assertEqual(shared.call_args.args, ("/autoteste",))
        route_trace.assert_not_called()

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
        self.assertEqual(result.text, "Briefing do dia.")
        self.assertEqual(result.action, "daily_briefing")
        self.assertTrue(result.contract["remote_policy"]["can_execute"])

    def test_action_response_is_polished(self):
        fake_trace = Mock()
        fake_trace.match = Mock(
            result={"intent": "investment_memory_answer", "target": "teste"},
            intent_level="pergunta",
            group_name="investment_questions",
            detector_name="detect_investment_question_command",
        )
        fake_trace.checked_detectors = 2
        fake_trace.checked_groups = ["investment_questions"]
        with (
            patch.object(gateway, "route_trace", return_value=fake_trace),
            patch.object(gateway, "execute_telegram_command", return_value="Juros/inflacao afetam precos. Nao e recomendacao."),
        ):
            result = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "teste"}},
                allowed_chat_ids={"123"},
            )

        self.assertEqual(result.text, "Juros/inflação afetam preços. Não é recomendação.")

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
        self.assertIn("confirmação no PC", result.text)
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
        self.assertIn("Confirmar ação remota", help_response.text)
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

    def test_remote_status_explains_current_permission_limits(self):
        result = gateway.handle_telegram_update(
            {"message": {"chat": {"id": 123}, "text": "status remoto"}},
            allowed_chat_ids={"123"},
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.status, "remote_mode_disabled")
        self.assertIn("leitura segura", result.text)
        self.assertIn("mídia/volume", result.text)
        self.assertIn("Bloqueado", result.text)

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

    def test_slash_retry_reuses_last_non_conversation_command(self):
        calls = []

        def fake_route_trace(text):
            calls.append(text)
            fake_trace = Mock()
            fake_trace.match = Mock(
                result={"intent": "daily_briefing", "target": None},
                intent_level="pergunta",
                group_name="daily",
                detector_name="detect_briefing",
            )
            fake_trace.checked_detectors = 2
            fake_trace.checked_groups = ["daily"]
            return fake_trace

        with (
            patch.object(gateway, "route_trace", side_effect=fake_route_trace),
            patch.object(gateway, "execute_telegram_command", return_value="Briefing."),
        ):
            first = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "briefing"}},
                allowed_chat_ids={"123"},
            )
            second = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "/retry"}},
                allowed_chat_ids={"123"},
            )

        self.assertTrue(first.ok)
        self.assertTrue(second.ok)
        self.assertEqual(calls, ["briefing", "briefing"])

    def test_undo_cancels_pending_remote_confirmation(self):
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
            undone = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "/undo"}},
                allowed_chat_ids={"123"},
            )
            confirm_after_undo = gateway.handle_telegram_update(
                {"message": {"chat": {"id": 123}, "text": "confirmar"}},
                allowed_chat_ids={"123"},
            )

        self.assertEqual(pending.status, "confirmation_required")
        self.assertTrue(undone.ok)
        self.assertIn("pendente cancelada", undone.text)
        self.assertEqual(confirm_after_undo.status, "confirmation_missing")
        execute_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
