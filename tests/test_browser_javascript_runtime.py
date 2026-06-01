import json
import unittest

from tools.browser_javascript_runtime import BrowserJavascriptRuntime
from tools.browser_dom_reader import PRODUCT_CARDS_MARKER


class FakeBrowserJavascriptRuntimeDeps:
    def __init__(self):
        self.active = True
        self.clipboard = "old"
        self.clipboard_reads = []
        self.calls = []

    def activate(self):
        return self.active

    def get_clipboard(self):
        if self.clipboard_reads:
            return self.clipboard_reads.pop(0)
        return self.clipboard

    def set_clipboard(self, text):
        self.clipboard = text
        self.calls.append(("clipboard", text))

    def shortcut(self, *keys):
        self.calls.append(("shortcut", keys))

    def type_text(self, text):
        self.calls.append(("type", text))

    def tap(self, key):
        self.calls.append(("tap", key))

    def sleep(self, seconds):
        self.calls.append(("sleep", seconds))


def make_runtime(deps: FakeBrowserJavascriptRuntimeDeps) -> BrowserJavascriptRuntime:
    return BrowserJavascriptRuntime(
        activate_browser_window=deps.activate,
        get_clipboard_text=deps.get_clipboard,
        set_clipboard_text=deps.set_clipboard,
        shortcut=deps.shortcut,
        type_text=deps.type_text,
        tap=deps.tap,
        sleep=deps.sleep,
        vk_control=17,
        vk_l=76,
        vk_v=86,
        vk_return=13,
    )


class BrowserJavascriptRuntimeTests(unittest.TestCase):
    def test_run_javascript_restores_clipboard(self):
        deps = FakeBrowserJavascriptRuntimeDeps()
        runtime = make_runtime(deps)

        self.assertTrue(runtime.run_javascript("alert(1)"))

        self.assertEqual(deps.calls[0], ("shortcut", (17, 76)))
        self.assertIn(("clipboard", "alert(1)"), deps.calls)
        self.assertEqual(deps.calls[-1], ("clipboard", "old"))

    def test_run_javascript_and_read_clipboard_returns_marked_payload(self):
        deps = FakeBrowserJavascriptRuntimeDeps()
        deps.clipboard_reads = ["old", "__MARK__ payload "]
        runtime = make_runtime(deps)

        result = runtime.run_javascript_and_read_clipboard("copy()", "__MARK__", timeout=0.1)

        self.assertEqual(result, "payload")
        self.assertEqual(deps.calls[-1], ("clipboard", "old"))

    def test_read_product_cards_uses_javascript_clipboard_runner(self):
        deps = FakeBrowserJavascriptRuntimeDeps()
        payload = json.dumps([{"text": "Notebook Lenovo Ideapad", "x": "10", "y": "20", "type": "Hyperlink"}])
        deps.clipboard_reads = ["old", PRODUCT_CARDS_MARKER + payload]
        runtime = make_runtime(deps)

        result = runtime.read_product_cards(limit=4)

        self.assertEqual(result[0]["text"], "Notebook Lenovo Ideapad")
        self.assertIn(("type", "javascript:"), deps.calls)


if __name__ == "__main__":
    unittest.main()
