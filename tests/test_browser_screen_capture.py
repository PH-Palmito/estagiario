import unittest

from tools.browser_screen_capture import BrowserScreenCapture


class FakeCaptureDeps:
    def __init__(self):
        self.clipboard = "old"
        self.clipboard_reads = []
        self.set_values = []
        self.shortcuts = []
        self.taps = []
        self.sleeps = []
        self.context_changes = []
        self.elements = []
        self.active = True
        self.ns = 100

    def activate(self):
        return self.active

    def get_clipboard(self):
        if self.clipboard_reads:
            return self.clipboard_reads.pop(0)
        return self.clipboard

    def set_clipboard(self, text):
        self.clipboard = text
        self.set_values.append(text)

    def shortcut(self, *codes):
        self.shortcuts.append(codes)

    def tap(self, code):
        self.taps.append(code)

    def read_elements(self, limit):
        return self.elements[:limit]

    def changed(self, *args):
        if self.context_changes:
            return self.context_changes.pop(0)
        return False

    def sleep(self, seconds):
        self.sleeps.append(seconds)

    def monotonic_ns(self):
        self.ns += 1
        return self.ns


def make_capture(deps: FakeCaptureDeps) -> BrowserScreenCapture:
    return BrowserScreenCapture(
        activate_browser_window=deps.activate,
        get_clipboard_text=deps.get_clipboard,
        set_clipboard_text=deps.set_clipboard,
        shortcut=deps.shortcut,
        tap=deps.tap,
        read_browser_elements=deps.read_elements,
        browser_context_recently_changed=deps.changed,
        vk_control=1,
        vk_a=65,
        vk_c=67,
        vk_escape=27,
        vk_l=76,
        sleep=deps.sleep,
        monotonic_ns=deps.monotonic_ns,
    )


class BrowserScreenCaptureTests(unittest.TestCase):
    def test_get_browser_url_copies_address_and_restores_clipboard(self):
        deps = FakeCaptureDeps()
        deps.clipboard_reads = ["old", "__ESTAGIARIO_BROWSER_URL__101__", "https://example.com/page"]
        capture = make_capture(deps)

        result = capture.get_browser_url()

        self.assertEqual(result, "https://example.com/page")
        self.assertIn((1, 76), deps.shortcuts)
        self.assertIn((1, 67), deps.shortcuts)
        self.assertEqual(deps.taps, [27])
        self.assertEqual(deps.clipboard, "old")

    def test_get_browser_url_returns_empty_when_browser_inactive(self):
        deps = FakeCaptureDeps()
        deps.active = False

        self.assertEqual(make_capture(deps).get_browser_url(), "")

    def test_read_page_text_via_clipboard_ranks_lines_and_restores_clipboard(self):
        deps = FakeCaptureDeps()
        page_text = "\n".join(["menu", "Smartphone Galaxy A55 256 GB", "R$ 1.899,00"])
        deps.clipboard_reads = ["old", page_text, page_text]
        capture = make_capture(deps)

        result = capture.read_page_text_via_clipboard(limit=3)

        self.assertIn("Smartphone Galaxy A55 256 GB", result)
        self.assertEqual(deps.taps, [27])
        self.assertEqual(deps.clipboard, "old")

    def test_read_screen_content_prefers_elements_when_quality_is_good(self):
        deps = FakeCaptureDeps()
        deps.elements = [
            {"text": "Notebook Lenovo com processador Ryzen e 16 GB de RAM"},
            {"text": "Smartphone Samsung Galaxy A55 com tela AMOLED"},
        ]
        capture = make_capture(deps)

        result = capture.read_screen_content_lines(
            item_limit=10,
            page_limit=10,
            page_url="https://loja.example.com",
            page_title="Loja",
        )

        self.assertFalse(result["prefer_page_text"])
        self.assertEqual(result["page_lines"], [])
        self.assertEqual(len(result["combined_lines"]), 2)

    def test_read_screen_content_uses_second_page_pass_when_first_is_weak(self):
        deps = FakeCaptureDeps()
        deps.elements = []
        deps.clipboard_reads = [
            "old",
            "menu",
            "menu",
            "old",
            "Notebook Lenovo com 16 GB de RAM e SSD 512 GB",
            "Notebook Lenovo com 16 GB de RAM e SSD 512 GB",
        ]
        deps.context_changes = [False, True]
        capture = make_capture(deps)

        result = capture.read_screen_content_lines(
            item_limit=5,
            page_limit=5,
            page_url="https://loja.example.com",
            page_title="Loja",
        )

        self.assertIn("Notebook Lenovo com 16 GB de RAM e SSD 512 GB", result["page_lines"])
        self.assertTrue(result["prefer_page_text"])


if __name__ == "__main__":
    unittest.main()
