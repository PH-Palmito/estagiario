import unittest
from unittest.mock import patch

from core.router_browser import detect_browser_command


class RouterBrowserTests(unittest.TestCase):
    def test_detects_new_tab(self):
        self.assertEqual(detect_browser_command("nova aba"), {"intent": "browser_new_tab", "target": None})

    def test_detects_close_tab(self):
        self.assertEqual(detect_browser_command("fechar aba"), {"intent": "browser_close_tab", "target": None})

    def test_detects_next_and_previous_tab(self):
        self.assertEqual(detect_browser_command("proxima aba"), {"intent": "browser_next_tab", "target": None})
        self.assertEqual(detect_browser_command("aba anterior"), {"intent": "browser_prev_tab", "target": None})

    def test_detects_browser_back(self):
        self.assertEqual(detect_browser_command("voltar"), {"intent": "browser_back", "target": None})

    def test_detects_browser_search(self):
        self.assertEqual(detect_browser_command("pesquise por python no navegador"), {"intent": "browser_search", "target": "python"})

    def test_detects_google_search(self):
        self.assertEqual(detect_browser_command("pesquise python"), {"intent": "google_search", "target": "python"})

    @patch("core.router_browser.load_current_topic", return_value={"topic": "PETR4 dividendos"})
    def test_detects_followup_search_from_current_topic(self, _load_current_topic):
        self.assertEqual(
            detect_browser_command("pesquise mais sobre isso"),
            {"intent": "google_search", "target": "PETR4 dividendos"},
        )


if __name__ == "__main__":
    unittest.main()
