import unittest

from core.router_screen import detect_screen_command


class RouterScreenTests(unittest.TestCase):
    def test_detects_screen_summary(self):
        self.assertEqual(detect_screen_command("resuma a tela"), {"intent": "browser_summarize_screen", "target": None})

    def test_detects_screen_description(self):
        self.assertEqual(detect_screen_command("o que tem na tela"), {"intent": "browser_describe_screen", "target": None})

    def test_detects_screen_explanation(self):
        self.assertEqual(detect_screen_command("detalha a tela"), {"intent": "browser_explain_screen", "target": None})

    def test_detects_translate_selection(self):
        self.assertEqual(detect_screen_command("traduzir selecionado"), {"intent": "browser_translate_selection", "target": None})

    def test_detects_translate_last_selection(self):
        self.assertEqual(detect_screen_command("traduzir isso"), {"intent": "browser_translate_last_selection", "target": None})

    def test_detects_read_selection(self):
        self.assertEqual(detect_screen_command("ler selecionado"), {"intent": "browser_read_selection", "target": None})

    def test_detects_read_more(self):
        self.assertEqual(detect_screen_command("ler mais"), {"intent": "browser_read_more", "target": None})

    def test_detects_cheapest_item(self):
        self.assertEqual(detect_screen_command("qual o mais barato"), {"intent": "browser_cheapest_listed_item", "target": None})

    def test_detects_click_listed_item(self):
        self.assertEqual(detect_screen_command("abrir terceiro item"), {"intent": "browser_click_listed_item", "target": 3})

    def test_detects_describe_listed_item(self):
        self.assertEqual(detect_screen_command("detalhes do segundo item"), {"intent": "browser_describe_listed_item", "target": 2})


if __name__ == "__main__":
    unittest.main()
