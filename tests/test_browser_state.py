import unittest
from unittest.mock import patch

from tools import browser_state


class BrowserStateTests(unittest.TestCase):
    def setUp(self):
        browser_state.clear_browser_snapshot()
        browser_state.set_last_selected_text("")

    def test_set_and_clear_browser_elements(self):
        browser_state.set_browser_elements([{"text": "Comprar", "x": 1, "y": 2}], context="ctx")

        self.assertEqual(browser_state.listed_browser_elements()[0]["text"], "Comprar")
        self.assertFalse(browser_state.browser_context_changed("ctx"))
        self.assertTrue(browser_state.browser_context_changed("ctx-2"))

        browser_state.clear_browser_snapshot(context="ctx-2")
        self.assertEqual(browser_state.listed_browser_elements(), [])
        self.assertFalse(browser_state.browser_context_changed("ctx-2"))

    def test_remember_text_items_builds_clickless_elements(self):
        browser_state.remember_text_items(["Item A", "Item B"], context="page")

        elements = browser_state.listed_browser_elements()
        self.assertEqual([item["text"] for item in elements], ["Item A", "Item B"])
        self.assertIsNone(elements[0]["x"])
        self.assertEqual(elements[0]["type"], "Text")

    def test_last_selected_text(self):
        browser_state.set_last_selected_text("texto")

        self.assertEqual(browser_state.last_selected_text(), "texto")

    def test_remember_browser_analysis_compacts_lines(self):
        with patch("tools.browser_state.remember_vision_analysis") as remember:
            browser_state.remember_browser_analysis(
                "  resumo   util ",
                lines=[" linha  um ", "", " linha   dois "],
                page_url="https://example.com",
                page_title="Pagina",
                source="pagina",
            )

        remember.assert_called_once()
        source, summary = remember.call_args.args[:2]
        details = remember.call_args.kwargs["details"]
        self.assertEqual(source, "pagina")
        self.assertEqual(summary, "resumo util")
        self.assertEqual(details["lines"], ["linha um", "linha dois"])


if __name__ == "__main__":
    unittest.main()
