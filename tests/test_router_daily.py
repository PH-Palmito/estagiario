import unittest

from core.router_daily import (
    detect_agenda_command,
    detect_briefing_command,
    detect_experience_memory_prompt,
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

    def test_detects_today_briefing_question_with_wake_word(self):
        result = detect_briefing_command("axel oq temos para hoje")

        self.assertEqual(result, {"intent": "daily_briefing", "target": None})

    def test_detects_background_briefing(self):
        result = detect_briefing_command("briefing em segundo plano")

        self.assertEqual(result, {"intent": "background_daily_briefing", "target": None})

    def test_detects_daily_routine(self):
        result = detect_briefing_command("axel prepara meu dia")

        self.assertEqual(result, {"intent": "daily_routine", "target": None})

    def test_detects_agenda_add(self):
        result = detect_agenda_command("adicionar na agenda revisar Axel hoje")

        self.assertEqual(result["intent"], "agenda_add")
        self.assertEqual(result["target"], "revisar Axel hoje")

    def test_detects_natural_commitment(self):
        result = detect_agenda_command("Axel eu tenho prova dia 12")

        self.assertEqual(result["intent"], "agenda_add")
        self.assertEqual(result["target"], "prova dia 12")

    def test_detects_agenda_today(self):
        result = detect_agenda_command("agenda de hoje")

        self.assertEqual(result, {"intent": "agenda_list_today", "target": None})

    def test_detects_reminder_add(self):
        result = detect_reminder_command("lembre de testar briefing amanha")

        self.assertEqual(result["intent"], "reminder_add")
        self.assertEqual(result["target"], "testar briefing amanha")

    def test_detects_trailing_reminder_as_agenda_commitment(self):
        result = detect_reminder_command("prova amanha me lembre")

        self.assertEqual(result["intent"], "agenda_add")
        self.assertEqual(result["target"], "prova amanha")

    def test_detects_standalone_time_as_reminder_reply(self):
        result = detect_reminder_command("7h da manha")

        self.assertEqual(result["intent"], "reminder_add")
        self.assertEqual(result["target"], "7h da manha")

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

    def test_detects_place_dislike_memory_prompt(self):
        result = detect_experience_memory_prompt("fui ao Restaurante Azul e nao gostei")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("Restaurante Azul", result["response"])

    def test_detects_bad_exam_result_prompt(self):
        result = detect_experience_memory_prompt("fiz uma prova hj e fui mal")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("marque uma revisao curta", result["response"])


if __name__ == "__main__":
    unittest.main()
