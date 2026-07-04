import unittest
from types import SimpleNamespace
from unittest.mock import patch

from services import telegram_polling


class TelegramPollingTests(unittest.TestCase):
    def test_send_telegram_message_polishes_text_payload(self):
        response = SimpleNamespace(raise_for_status=lambda: None)

        with patch.object(telegram_polling.requests, "post", return_value=response) as post:
            telegram_polling.send_telegram_message("token", "123", "Nao encontrei precos. O que voce quer")

        payload = post.call_args.kwargs["json"]
        self.assertEqual(payload["text"], "Não encontrei preços. O que você quer.")

    def test_polling_passes_audio_transcriber_to_gateway(self):
        calls = []
        stop_calls = {"count": 0}

        def stop_when():
            stop_calls["count"] += 1
            return stop_calls["count"] > 1

        response = SimpleNamespace(
            raise_for_status=lambda: None,
            json=lambda: {
                "result": [
                    {
                        "update_id": 10,
                        "message": {"chat": {"id": 123}, "voice": {"file_id": "voice-1"}},
                    }
                ]
            },
        )
        gateway_response = SimpleNamespace(
            chat_id="123",
            text="",
            status="audio_transcription_unavailable",
            action="telegram_audio",
            ok=False,
            reply_markup=None,
            callback_query_id="",
        )

        def transcriber(_request):
            return "briefing"

        with (
            patch.object(telegram_polling.requests, "get", return_value=response),
            patch("services.telegram_gateway.handle_telegram_update", side_effect=lambda update, **kwargs: calls.append(kwargs) or gateway_response),
            patch("services.telegram_gateway.log_telegram_event"),
            patch.object(telegram_polling.time, "sleep"),
        ):
            telegram_polling.poll_telegram_updates(
                token="token",
                allowed_chat_ids={"123"},
                state=telegram_polling.TelegramPollingState(),
                stop_when=stop_when,
                transcribe_audio=transcriber,
            )

        self.assertEqual(calls[0]["allowed_chat_ids"], {"123"})
        self.assertIs(calls[0]["transcribe_audio"], transcriber)


if __name__ == "__main__":
    unittest.main()
