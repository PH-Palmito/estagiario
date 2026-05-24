import unittest

from tools.browser_page_text import (
    rank_page_text_lines,
    selected_text_items,
    strip_gallery_suffix,
    useful_page_text_lines,
)


class BrowserPageTextTests(unittest.TestCase):
    def test_strip_gallery_suffix(self):
        self.assertEqual(strip_gallery_suffix("Notebook Lenovo imagem - 1/5"), "Notebook Lenovo")

    def test_rank_page_text_lines_prioritizes_product_lines(self):
        text = "\n".join(
            [
                "menu",
                "cookie",
                "Smartphone Galaxy A55 256 GB",
                "R$ 1.899,00",
                "departamentos",
            ]
        )

        result = rank_page_text_lines(text, limit=3)

        self.assertIn("Smartphone Galaxy A55 256 GB", result)
        self.assertNotIn("cookie", result)

    def test_rank_page_text_lines_prioritizes_finance_lines(self):
        text = "\n".join(["Patrimonio", "R$ 8.409,14", "Rentabilidade 15,57%", "menu"])

        result = rank_page_text_lines(text, limit=3, page_url="https://investidor10.com.br/carteira")

        self.assertTrue(any("Patrimonio" in line for line in result))
        self.assertTrue(any("Rentabilidade" in line for line in result))

    def test_selected_text_items_pairs_product_with_price(self):
        text = "\n".join(["Smartphone Motorola Edge 128 GB", "R$ 1.299,00", "Cupom disponivel"])

        result = selected_text_items(text)

        self.assertEqual(result, ["Smartphone Motorola Edge 128 GB - R$ 1.299,00"])

    def test_useful_page_text_lines_filters_noise(self):
        text = "\n".join(["javascript:void(0)", "Notebook Acer Aspire em oferta", "R$ 2.499,00"])

        result = useful_page_text_lines(text, limit=2)

        self.assertIn("Notebook Acer Aspire em oferta", result)
        self.assertNotIn("javascript:void(0)", result)


if __name__ == "__main__":
    unittest.main()
