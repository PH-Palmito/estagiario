import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import browser_product_cache as cache


class BrowserProductCacheTests(unittest.TestCase):
    def test_save_and_format_product_snapshot(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "products.json"
            with patch.object(cache, "PRODUCT_CACHE_PATH", path):
                cache.save_product_snapshot(
                    [
                        {"text": "Notebook Gamer R$ 4.999,00", "x": 10, "y": 20},
                        {"text": "Cupom sem produto"},
                    ],
                    context="mercado livre",
                )
                formatted = cache.format_cached_products()

        self.assertIn("Notebook Gamer", formatted)
        self.assertNotIn("Cupom sem produto", formatted)

    def test_cheapest_cached_product_uses_lowest_price(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "products.json"
            with patch.object(cache, "PRODUCT_CACHE_PATH", path):
                cache.save_product_snapshot(
                    [
                        {"text": "Produto caro R$ 20,00"},
                        {"text": "Produto barato R$ 10,00"},
                    ]
                )
                result = cache.cheapest_cached_product()

        self.assertIn("item 2", result)
        self.assertIn("Produto barato", result)

    def test_expired_cache_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "products.json"
            with patch.object(cache, "PRODUCT_CACHE_PATH", path), patch("memory.browser_product_cache.time.time", return_value=1000):
                cache.save_product_snapshot([{"text": "Produto R$ 10,00"}])
            with patch.object(cache, "PRODUCT_CACHE_PATH", path), patch("memory.browser_product_cache.time.time", return_value=5000):
                self.assertEqual(cache.cached_product_items(), [])


if __name__ == "__main__":
    unittest.main()
