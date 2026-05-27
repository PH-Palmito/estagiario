import unittest
from unittest.mock import patch

from actions import ensure_default_actions, execute_action
from services import briefing_service, investment_service, vision_service


class ServicesLayerTests(unittest.TestCase):
    def test_briefing_service_delegates_to_tool(self):
        with patch("services.briefing_service.build_daily_briefing", return_value="briefing"):
            self.assertEqual(briefing_service.daily_briefing(), "briefing")

    def test_investment_service_delegates_to_tool(self):
        with patch("services.investment_service.financial_report", return_value="relatorio"):
            self.assertEqual(investment_service.investment_report(), "relatorio")

    def test_vision_service_delegates_to_tool(self):
        with patch("services.vision_service.analyze_screen_image", return_value="tela"):
            self.assertEqual(vision_service.analyze_screen(), "tela")

    def test_registered_daily_briefing_action_uses_service_layer(self):
        ensure_default_actions()
        with patch("services.briefing_service.daily_briefing", return_value="via service"):
            result = execute_action("daily_briefing", {})

        self.assertEqual(result, "via service")

    def test_registered_vision_action_uses_service_layer(self):
        ensure_default_actions()
        with patch("services.vision_service.analyze_screen", return_value="visao service"):
            result = execute_action("image_analyze_screen", {})

        self.assertEqual(result, "visao service")


if __name__ == "__main__":
    unittest.main()
