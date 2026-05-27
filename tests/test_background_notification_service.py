import unittest
from unittest.mock import patch

from services.background_notification_service import format_background_notification, publish_background_notification


class BackgroundNotificationServiceTests(unittest.TestCase):
    def test_formats_success_notification_for_ui(self):
        payload = format_background_notification(
            {"name": "daily_briefing", "status": "succeeded", "message": "Resumo pronto"}
        )

        self.assertEqual(payload["kind"], "background")
        self.assertEqual(payload["level"], "info")
        self.assertIn("daily_briefing terminou", payload["text"])

    def test_formats_failure_notification_as_warning(self):
        payload = format_background_notification({"name": "visao", "status": "failed", "error": "boom"})

        self.assertEqual(payload["level"], "warning")
        self.assertIn("visao falhou: boom", payload["text"])

    def test_publish_background_notification_appends_ui_notification(self):
        with (
            patch("memory.ui_state.append_ui_notification") as notify_mock,
            patch("memory.ui_state.load_ui_state", return_value={"voice_notifications_enabled": False}),
            patch("memory.ui_state.append_voice_notification") as voice_mock,
        ):
            published = publish_background_notification(
                {"name": "carteira", "status": "succeeded", "message": "ok"}
            )

        self.assertTrue(published)
        notify_mock.assert_called_once_with("background", "carteira terminou: ok", level="info")
        voice_mock.assert_not_called()

    def test_publish_background_notification_queues_voice_when_allowed(self):
        with (
            patch("memory.ui_state.append_ui_notification"),
            patch("memory.ui_state.load_ui_state", return_value={"voice_notifications_enabled": True, "mode": "comando"}),
            patch("memory.ui_state.append_voice_notification") as voice_mock,
        ):
            published = publish_background_notification(
                {"name": "daily_briefing", "status": "succeeded", "message": "ok"}
            )

        self.assertTrue(published)
        voice_mock.assert_called_once_with("daily_briefing terminou. ok", source="background")


if __name__ == "__main__":
    unittest.main()
