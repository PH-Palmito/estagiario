import unittest

from core.router_apps import (
    detect_close_app,
    detect_open_app,
    detect_open_chatgpt,
    detect_open_url,
    detect_window_command,
)


class RouterAppsTests(unittest.TestCase):
    def test_detects_open_known_app(self):
        result = detect_open_app("abre calculadora")

        self.assertEqual(result, {"intent": "open_app", "target": "calculadora"})

    def test_detects_smart_open_unknown_target(self):
        result = detect_open_app("abre android studio")

        self.assertEqual(result, {"intent": "smart_open", "target": "android studio"})

    def test_vague_open_target_asks_for_clarification(self):
        result = detect_open_app("abre isso")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("alvo ficou vago", result["response"])

    def test_detects_close_known_app(self):
        result = detect_close_app("feche o spotify")

        self.assertEqual(result, {"intent": "close_app", "target": "spotify"})

    def test_detects_window_focus(self):
        result = detect_window_command("foca no chrome")

        self.assertEqual(result, {"intent": "focus_app", "target": "chrome"})

    def test_detects_window_context_maximize(self):
        result = detect_window_command("maximiza")

        self.assertEqual(result, {"intent": "maximize_app", "target": None})

    def test_detects_site_url(self):
        result = detect_open_url("abre youtube")

        self.assertEqual(result, {"intent": "open_url", "target": "https://www.youtube.com"})

    def test_detects_direct_url(self):
        result = detect_open_url("abre www.example.com")

        self.assertEqual(result, {"intent": "open_url", "target": "https://www.example.com"})

    def test_detects_chatgpt_direct_command(self):
        result = detect_open_chatgpt("abre chatgpt")

        self.assertEqual(result, {"intent": "open_chatgpt", "target": None})


if __name__ == "__main__":
    unittest.main()
