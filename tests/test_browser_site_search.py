import unittest

from tools.browser_site_search import browser_search_site


class BrowserSiteSearchTests(unittest.TestCase):
    def test_searches_known_sites_directly(self):
        opened = []

        result = browser_search_site(
            "mercadolivre.com.br",
            "fone bluetooth",
            open_url=lambda url, **kwargs: opened.append((url, kwargs)),
        )

        self.assertEqual(result, "Pesquisando fone bluetooth no Mercado Livre em uma nova aba.")
        self.assertEqual(opened[0][0], "https://lista.mercadolivre.com.br/fone+bluetooth")
        self.assertEqual(opened[0][1]["new"], 2)

    def test_falls_back_to_google_site_search(self):
        opened = []

        result = browser_search_site(
            "example.com",
            "teste rapido",
            open_url=lambda url, **kwargs: opened.append((url, kwargs)),
        )

        self.assertEqual(result, "Pesquisando teste rapido em example.com em uma nova aba.")
        self.assertIn("site%3Aexample.com", opened[0][0])

    def test_requires_site_and_query(self):
        self.assertEqual(
            browser_search_site("", "fone", open_url=lambda *_args, **_kwargs: None),
            "Qual site e qual pesquisa?",
        )


if __name__ == "__main__":
    unittest.main()
