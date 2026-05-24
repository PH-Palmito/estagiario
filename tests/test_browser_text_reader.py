import unittest

from tools.browser_text_reader import BrowserTextReader, compact_selected_text


def make_reader(*, active=True, app_active=True, clipboard_values=None):
    calls = []
    values = list(clipboard_values or ["old", "copied"])

    def get_clipboard():
        if values:
            return values.pop(0)
        return ""

    reader = BrowserTextReader(
        activate_browser_window=lambda: active,
        activate_window_names=lambda names: app_active,
        get_clipboard_text=get_clipboard,
        set_clipboard_text=lambda text: calls.append(("set_clipboard", text)),
        shortcut=lambda *keys: calls.append(("shortcut", keys)),
        tap=lambda key: calls.append(("tap", key)),
        sleep=lambda seconds: calls.append(("sleep", seconds)),
        vk_control=17,
        vk_c=67,
        vk_a=65,
        vk_escape=27,
    )
    return reader, calls


class BrowserTextReaderTests(unittest.TestCase):
    def test_read_selected_text_copies_and_restores_clipboard(self):
        reader, calls = make_reader(clipboard_values=["old", "selecionado"])

        result = reader.read_selected_text()

        self.assertEqual(result, "selecionado")
        self.assertEqual(
            calls,
            [
                ("set_clipboard", ""),
                ("shortcut", (17, 67)),
                ("sleep", 0.25),
                ("set_clipboard", "old"),
            ],
        )

    def test_read_selected_text_returns_none_when_browser_is_inactive(self):
        reader, calls = make_reader(active=False)

        self.assertIsNone(reader.read_selected_text())
        self.assertEqual(calls, [])

    def test_read_full_page_text_uses_select_all_copy_escape_and_restore(self):
        reader, calls = make_reader(clipboard_values=["old", "pagina inteira"])

        result = reader.read_full_page_text_from_browser(wait_seconds=0.5)

        self.assertEqual(result, "pagina inteira")
        self.assertEqual(
            calls,
            [
                ("set_clipboard", ""),
                ("shortcut", (17, 65)),
                ("sleep", 0.12),
                ("shortcut", (17, 67)),
                ("sleep", 0.5),
                ("tap", 27),
                ("set_clipboard", "old"),
            ],
        )

    def test_read_full_page_text_can_target_app_name(self):
        reader, calls = make_reader(app_active=True, clipboard_values=["old", "texto app"])

        result = reader.read_full_page_text_from_browser(app_name="msedge")

        self.assertEqual(result, "texto app")
        self.assertTrue(calls)

    def test_compact_selected_text_trims_whitespace_and_length(self):
        self.assertEqual(compact_selected_text("  ola   mundo  "), "ola mundo")
        self.assertEqual(compact_selected_text("abcdef", max_length=5), "ab...")


if __name__ == "__main__":
    unittest.main()
