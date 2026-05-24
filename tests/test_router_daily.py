import unittest

from core.router_daily import (
    detect_agenda_command,
    detect_briefing_command,
    detect_map_command,
    detect_reminder_command,
    detect_weather_command,
)


class RouterDailyTests(unittest.TestCase):
    def test_detects_weather_with_location(self):
        result = detect_weather_command("clima em Salvador")

        self.assertEqual(result["intent"], "weather_summary")
        self.assertEqual(result["target"], "Salvador")

    def test_detects_briefing(self):
        result = detect_briefing_command("briefing")

        self.assertEqual(result, {"intent": "daily_briefing", "target": None})

    def test_detects_daily_routine(self):
        result = detect_briefing_command("comecar meu dia")

        self.assertEqual(result, {"intent": "daily_routine", "target": None})

    def test_detects_agenda_add(self):
        result = detect_agenda_command("adicionar na agenda revisar Axel hoje")

        self.assertEqual(result["intent"], "agenda_add")
        self.assertEqual(result["target"], "revisar Axel hoje")

    def test_detects_agenda_today(self):
        result = detect_agenda_command("agenda de hoje")

        self.assertEqual(result, {"intent": "agenda_list_today", "target": None})

    def test_detects_reminder_add(self):
        result = detect_reminder_command("lembre de testar briefing amanha")

        self.assertEqual(result["intent"], "reminder_add")
        self.assertEqual(result["target"], "testar briefing amanha")

    def test_detects_reminder_list(self):
        result = detect_reminder_command("lembretes")

        self.assertEqual(result, {"intent": "reminder_list", "target": None})

    def test_detects_map_place(self):
        result = detect_map_command("mostre o mapa de Salvador")

        self.assertEqual(result["intent"], "ui_show_map")
        self.assertEqual(result["target"]["kind"], "place")
        self.assertEqual(result["target"]["location"], "Salvador")
        self.assertEqual(result["target"]["label"], "Salvador")
        self.assertIn("google.com/maps/search", result["target"]["url"])


if __name__ == "__main__":
    unittest.main()
