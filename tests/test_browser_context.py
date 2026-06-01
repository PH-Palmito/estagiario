import unittest

from tools.browser_context import browser_context_signature, refresh_browser_context


class BrowserContextTests(unittest.TestCase):
    def test_builds_signature_from_title_url_and_capture_hash(self):
        result = browser_context_signature(
            get_title=lambda: "  Mercado   Livre - Chrome ",
            get_url=lambda: "https://www.mercadolivre.com.br/ofertas?x=1",
            get_capture_hash=lambda: "abcdef1234567890zzzz",
            normalize_text=lambda text: text.lower().replace(" ", "-"),
        )

        self.assertEqual(
            result,
            "mercado-livre---chrome|www.mercadolivre.com.br/ofertas|abcdef1234567890",
        )

    def test_signature_returns_empty_without_title(self):
        result = browser_context_signature(
            get_title=lambda: "",
            get_url=lambda: "https://example.com",
            get_capture_hash=lambda: "hash",
            normalize_text=lambda text: text,
        )

        self.assertEqual(result, "")

    def test_refresh_clears_snapshot_when_context_changed(self):
        calls = []

        result = refresh_browser_context(
            get_signature=lambda: "ctx-2",
            context_changed=lambda context: context == "ctx-2",
            clear_snapshot=lambda **kwargs: calls.append(("clear", kwargs)),
            mark_context=lambda context: calls.append(("mark", context)),
        )

        self.assertEqual(result, "ctx-2")
        self.assertEqual(calls, [("clear", {"context": "ctx-2"})])

    def test_refresh_marks_context_when_unchanged(self):
        calls = []

        result = refresh_browser_context(
            get_signature=lambda: "ctx-1",
            context_changed=lambda _context: False,
            clear_snapshot=lambda **kwargs: calls.append(("clear", kwargs)),
            mark_context=lambda context: calls.append(("mark", context)),
        )

        self.assertEqual(result, "ctx-1")
        self.assertEqual(calls, [("mark", "ctx-1")])


if __name__ == "__main__":
    unittest.main()
