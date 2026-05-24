import unittest

from core.router_browser_controls import detect_browser_control_command


class RouterBrowserControlsTests(unittest.TestCase):
    def test_detects_scroll_down(self):
        self.assertEqual(detect_browser_control_command("role para baixo"), {"intent": "browser_scroll_down", "target": None})

    def test_detects_small_scroll_up(self):
        self.assertEqual(detect_browser_control_command("sobe um pouco"), {"intent": "browser_scroll_up_small", "target": None})

    def test_detects_scroll_top_and_bottom(self):
        self.assertEqual(detect_browser_control_command("topo da pagina"), {"intent": "browser_scroll_top", "target": None})
        self.assertEqual(detect_browser_control_command("fim da pagina"), {"intent": "browser_scroll_bottom", "target": None})

    def test_detects_browser_navigation_controls(self):
        self.assertEqual(detect_browser_control_command("voltar pagina"), {"intent": "browser_back", "target": None})
        self.assertEqual(detect_browser_control_command("avancar pagina"), {"intent": "browser_forward", "target": None})
        self.assertEqual(detect_browser_control_command("atualizar pagina"), {"intent": "browser_refresh", "target": None})

    def test_detects_open_first_and_focused_item(self):
        self.assertEqual(detect_browser_control_command("abrir primeiro resultado"), {"intent": "browser_open_first_result", "target": None})
        self.assertEqual(detect_browser_control_command("abrir selecionado"), {"intent": "browser_open_focused_item", "target": None})

    def test_detects_clicks(self):
        self.assertEqual(detect_browser_control_command("clicar no centro"), {"intent": "browser_click_center", "target": None})
        self.assertEqual(detect_browser_control_command("clique comprar"), {"intent": "browser_click_text", "target": "comprar"})

    def test_detects_zoom(self):
        self.assertEqual(detect_browser_control_command("aumentar zoom"), {"intent": "browser_zoom_in", "target": None})
        self.assertEqual(detect_browser_control_command("diminuir zoom"), {"intent": "browser_zoom_out", "target": None})
        self.assertEqual(detect_browser_control_command("resetar zoom"), {"intent": "browser_zoom_reset", "target": None})

    def test_detects_find_on_page(self):
        self.assertEqual(detect_browser_control_command("procurar dividendos na pagina"), {"intent": "browser_find", "target": "dividendos"})


if __name__ == "__main__":
    unittest.main()
