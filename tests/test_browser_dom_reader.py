import json
import unittest

from tools.browser_dom_reader import (
    PRODUCT_CARDS_MARKER,
    build_product_cards_script,
    parse_product_cards_payload,
)


class BrowserDomReaderTests(unittest.TestCase):
    def test_build_product_cards_script_contains_marker_and_limit(self):
        script = build_product_cards_script(limit=7)

        self.assertIn(json.dumps(PRODUCT_CARDS_MARKER), script)
        self.assertIn("const limit=7;", script)
        self.assertIn("querySelectorAll", script)

    def test_parse_product_cards_payload_normalizes_valid_rows(self):
        payload = json.dumps(
            [
                {"text": "  Smartphone Galaxy A55  ", "x": "100", "y": "200", "type": "Hyperlink"},
                {"text": "Smartphone Galaxy A55", "x": "100", "y": "200", "type": "Hyperlink"},
                {"text": "curto", "x": "1", "y": "2"},
                {"text": "Notebook Lenovo 16 GB", "x": 300, "y": 400, "type": ""},
            ]
        )

        result = parse_product_cards_payload(payload, limit=5)

        self.assertEqual(
            result,
            [
                {
                    "text": "Smartphone Galaxy A55",
                    "x": 100,
                    "y": 200,
                    "type": "Hyperlink",
                    "source": "dom_product",
                },
                {
                    "text": "Notebook Lenovo 16 GB",
                    "x": 300,
                    "y": 400,
                    "type": "Hyperlink",
                    "source": "dom_product",
                },
            ],
        )

    def test_parse_product_cards_payload_handles_invalid_json_and_coordinates(self):
        self.assertEqual(parse_product_cards_payload("{"), [])

        payload = json.dumps([{"text": "Smartphone Galaxy A55", "x": "x", "y": 200}])

        self.assertEqual(parse_product_cards_payload(payload), [])


if __name__ == "__main__":
    unittest.main()
