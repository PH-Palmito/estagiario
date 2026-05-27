import unittest

from services.voice_notification_service import plan_background_voice_notification, speak_next_pending_voice_notification


class VoiceNotificationServiceTests(unittest.TestCase):
    def test_voice_notification_is_disabled_by_default(self):
        plan = plan_background_voice_notification(
            {"name": "daily_briefing", "status": "succeeded", "message": "ok"},
            {},
        )

        self.assertFalse(plan.should_speak)
        self.assertIn("desligadas", plan.reason)

    def test_important_background_task_can_be_spoken_when_enabled(self):
        plan = plan_background_voice_notification(
            {"name": "daily_briefing", "status": "succeeded", "message": "Resumo pronto"},
            {"voice_notifications_enabled": True, "mode": "comando"},
        )

        self.assertTrue(plan.should_speak)
        self.assertEqual(plan.text, "daily_briefing terminou. Resumo pronto")

    def test_failure_can_be_spoken_even_for_unknown_task(self):
        plan = plan_background_voice_notification(
            {"name": "unit_task", "status": "failed", "error": "boom"},
            {"voice_notifications_enabled": True, "mode": "comando"},
        )

        self.assertTrue(plan.should_speak)
        self.assertEqual(plan.text, "unit_task falhou. boom")

    def test_focus_or_silent_mode_blocks_voice_notification(self):
        for mode in ("foco", "silencioso"):
            plan = plan_background_voice_notification(
                {"name": "daily_briefing", "status": "succeeded", "message": "ok"},
                {"voice_notifications_enabled": True, "mode": mode},
            )
            self.assertFalse(plan.should_speak)

    def test_low_priority_success_does_not_speak(self):
        plan = plan_background_voice_notification(
            {"name": "unit_task", "status": "succeeded", "message": "ok"},
            {"voice_notifications_enabled": True, "mode": "comando"},
        )

        self.assertFalse(plan.should_speak)

    def test_speak_next_pending_voice_notification_speaks_one_item(self):
        spoken = []
        popped = [{"text": "Carteira terminou."}]

        result = speak_next_pending_voice_notification(
            voice_mode=True,
            speak=lambda text, **kwargs: spoken.append((text, kwargs)),
            load_ui_state=lambda: {"mode": "comando", "voice_notifications_pending": [{"text": "Carteira terminou."}]},
            pop_next_voice_notification=lambda: popped.pop(0),
        )

        self.assertTrue(result)
        self.assertEqual(spoken[0][0], "Carteira terminou.")
        self.assertFalse(spoken[0][1]["wait_for_playback"])

    def test_speak_next_pending_voice_notification_respects_focus_mode(self):
        spoken = []

        result = speak_next_pending_voice_notification(
            voice_mode=True,
            speak=lambda text, **kwargs: spoken.append(text),
            load_ui_state=lambda: {"mode": "foco", "voice_notifications_pending": [{"text": "Nao falar"}]},
            pop_next_voice_notification=lambda: self.fail("should not pop in focus mode"),
        )

        self.assertFalse(result)
        self.assertEqual(spoken, [])


if __name__ == "__main__":
    unittest.main()
