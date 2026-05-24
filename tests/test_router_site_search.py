import unittest

from core.router_site_search import detect_site_search_command


class RouterSiteSearchTests(unittest.TestCase):
    def test_detects_site_search(self):
        self.assertEqual(
            detect_site_search_command("pesquise notebook no mercado livre"),
            {"intent": "browser_search_site", "target": {"query": "notebook", "site": "https://www.mercadolivre.com.br"}},
        )

    def test_detects_polite_site_search(self):
        self.assertEqual(
            detect_site_search_command("pode pesquisar mouse no google"),
            {"intent": "browser_search_site", "target": {"query": "mouse", "site": "https://www.google.com"}},
        )

    def test_detects_incomplete_mercado_livre_prompt(self):
        self.assertEqual(
            detect_site_search_command("no mercado livre"),
            {"intent": "respond", "target": None, "response": "Qual produto voce quer pesquisar no Mercado Livre?"},
        )


if __name__ == "__main__":
    unittest.main()
