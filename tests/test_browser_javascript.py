import unittest

from tools.browser_javascript import run_browser_javascript, run_browser_javascript_and_read_clipboard


class BrowserJavascriptTests(unittest.TestCase):
    def test_run_browser_javascript_restores_clipboard(self):
        calls = []
        clipboard = {"text": "old"}

        result = run_browser_javascript(
            "alert(1)",
            activate_browser_window=lambda: True,
            get_clipboard_text=lambda: clipboard["text"],
            set_clipboard_text=lambda text: calls.append(("clipboard", text)) or clipboard.update(text=text),
            shortcut=lambda *keys: calls.append(("shortcut", keys)),
            type_text=lambda text: calls.append(("type", text)),
            tap=lambda key: calls.append(("tap", key)),
            sleep=lambda seconds: calls.append(("sleep", seconds)),
            vk_control=17,
            vk_l=76,
            vk_v=86,
            vk_return=13,
        )

        self.assertTrue(result)
        self.assertEqual(calls[0], ("shortcut", (17, 76)))
        self.assertIn(("clipboard", "alert(1)"), calls)
        self.assertEqual(calls[-1], ("clipboard", "old"))

    def test_run_browser_javascript_returns_false_when_inactive(self):
        self.assertFalse(
            run_browser_javascript(
                "alert(1)",
                activate_browser_window=lambda: False,
                get_clipboard_text=lambda: "",
                set_clipboard_text=lambda _text: None,
                shortcut=lambda *_keys: None,
                type_text=lambda _text: None,
                tap=lambda _key: None,
                sleep=lambda _seconds: None,
                vk_control=17,
                vk_l=76,
                vk_v=86,
                vk_return=13,
            )
        )

    def test_run_browser_javascript_and_read_clipboard_returns_marked_payload(self):
        calls = []
        clipboard_values = iter(["old", "__MARK__ payload "])
        restored = []

        result = run_browser_javascript_and_read_clipboard(
            "copy()",
            "__MARK__",
            activate_browser_window=lambda: True,
            get_clipboard_text=lambda: next(clipboard_values),
            set_clipboard_text=lambda text: restored.append(text),
            shortcut=lambda *keys: calls.append(("shortcut", keys)),
            type_text=lambda text: calls.append(("type", text)),
            tap=lambda key: calls.append(("tap", key)),
            sleep=lambda seconds: calls.append(("sleep", seconds)),
            vk_control=17,
            vk_l=76,
            vk_v=86,
            vk_return=13,
            timeout=0.1,
        )

        self.assertEqual(result, "payload")
        self.assertEqual(restored[-1], "old")

    def test_run_browser_javascript_and_read_clipboard_ignores_unmarked_payload(self):
        clipboard_values = iter(["old", "plain"])

        result = run_browser_javascript_and_read_clipboard(
            "copy()",
            "__MARK__",
            activate_browser_window=lambda: True,
            get_clipboard_text=lambda: next(clipboard_values),
            set_clipboard_text=lambda _text: None,
            shortcut=lambda *_keys: None,
            type_text=lambda _text: None,
            tap=lambda _key: None,
            sleep=lambda _seconds: None,
            vk_control=17,
            vk_l=76,
            vk_v=86,
            vk_return=13,
        )

        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
