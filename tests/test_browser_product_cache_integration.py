import unittest
from unittest.mock import patch

from tools import browser_state


class BrowserProductCacheIntegrationTests(unittest.TestCase):
    def test_set_browser_elements_saves_product_snapshot(self):
        with patch("tools.browser_state.save_product_snapshot") as save:
            browser_state.set_browser_elements([{"text": "Produto R$ 10,00"}], context="mercado livre")

        save.assert_called_once_with([{"text": "Produto R$ 10,00"}], context="mercado livre")


if __name__ == "__main__":
    unittest.main()
