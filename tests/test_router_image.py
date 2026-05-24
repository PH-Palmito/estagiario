import unittest

from core.router_image import detect_image_analysis_command


class RouterImageTests(unittest.TestCase):
    def test_browser_image_analysis(self):
        self.assertEqual(
            detect_image_analysis_command("analisar imagem no navegador"),
            {"intent": "image_analyze_browser", "target": None},
        )

    def test_clipboard_image_analysis(self):
        self.assertEqual(
            detect_image_analysis_command("analisar imagem copiada"),
            {"intent": "image_analyze_clipboard", "target": None},
        )

    def test_screen_graph_analysis(self):
        self.assertEqual(
            detect_image_analysis_command("analisar grafico"),
            {"intent": "image_analyze_screen_graph", "target": None},
        )

    def test_screen_image_analysis(self):
        self.assertEqual(
            detect_image_analysis_command("interpretar imagem"),
            {"intent": "image_analyze_screen", "target": None},
        )

    def test_graph_file_analysis_keeps_original_target(self):
        self.assertEqual(
            detect_image_analysis_command(r"analisar grafico C:\prints\grafico.png"),
            {"intent": "image_analyze_graph", "target": r"C:\prints\grafico.png"},
        )

    def test_image_file_analysis_keeps_original_target(self):
        self.assertEqual(
            detect_image_analysis_command(r"analisar imagem C:\prints\tela.png"),
            {"intent": "image_analyze", "target": r"C:\prints\tela.png"},
        )


if __name__ == "__main__":
    unittest.main()
