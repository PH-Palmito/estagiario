import unittest
from unittest.mock import patch

from actions import ensure_default_actions, get_action
from core.normalizer import normalize_action
from core.router import route


class TelegramActionsTests(unittest.TestCase):
    def test_default_actions_include_telegram(self):
        ensure_default_actions()

        self.assertIsNotNone(get_action("telegram.status"))
        self.assertIsNotNone(get_action("telegram.recent_chats"))
        self.assertIsNotNone(get_action("telegram.start_bot"))
        self.assertIsNotNone(get_action("telegram.simulate_message"))

    def test_router_detects_telegram_status(self):
        self.assertEqual(route("status do telegram")["intent"], "telegram.status")
        self.assertEqual(route("descobrir chat id telegram")["intent"], "telegram.recent_chats")
        self.assertEqual(route("iniciar bot telegram")["intent"], "telegram.start_bot")

    def test_normalizer_maps_simulation(self):
        raw = route("simular telegram briefing")
        command = normalize_action(raw)

        self.assertEqual(command.action, "telegram.simulate_message")
        self.assertEqual(command.params["text"], "briefing")

    def test_start_bot_requires_token(self):
        ensure_default_actions()
        action = get_action("telegram.start_bot")
        with patch("tools.telegram_tools.TELEGRAM_BOT_TOKEN", ""):
            result = action.handler({})

        self.assertIn("AXEL_TELEGRAM_BOT_TOKEN", result)


if __name__ == "__main__":
    unittest.main()
