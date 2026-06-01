import json
import unittest

from tools.browser_product_cards import read_product_cards_via_javascript


class BrowserProductCardsTests(unittest.TestCase):
    def test_reads_cards_via_javascript_runner(self):
        calls = []
        payload = json.dumps([
            {"text": "Notebook Lenovo Ideapad", "x": "10", "y": "20", "type": "Hyperlink"},
            {"text": "curto", "x": "1", "y": "2"},
        ])

        result = read_product_cards_via_javascript(
            run_javascript_and_read_clipboard=lambda script, marker: calls.append((script, marker)) or payload,
            limit=4,
        )

        self.assertIn("const limit=4;", calls[0][0])
        self.assertTrue(calls[0][1].startswith("__ESTAGIARIO_PRODUCTS__"))
        self.assertEqual(result[0]["text"], "Notebook Lenovo Ideapad")
        self.assertEqual(result[0]["source"], "dom_product")

    def test_returns_empty_when_runner_returns_invalid_payload(self):
        result = read_product_cards_via_javascript(
            run_javascript_and_read_clipboard=lambda _script, _marker: "{",
            limit=4,
        )

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
