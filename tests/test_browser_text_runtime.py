import unittest

from tools.browser_text_runtime import BrowserTextRuntime


class FakeBrowserTextRuntimeDeps:
    def __init__(self):
        self.active = True
        self.app_active = True
        self.clipboard = "old"
        self.clipboard_reads = []
        self.calls = []
        self.last_text = ""
        self.analyses = []
        self.text_items = []
        self.ask_response = "a traducao e: ola mundo"

    def activate(self):
        return self.active

    def activate_names(self, _names):
        return self.app_active

    def get_clipboard(self):
        if self.clipboard_reads:
            return self.clipboard_reads.pop(0)
        return self.clipboard

    def set_clipboard(self, text):
        self.clipboard = text
        self.calls.append(("set_clipboard", text))

    def shortcut(self, *keys):
        self.calls.append(("shortcut", keys))

    def tap(self, key):
        self.calls.append(("tap", key))

    def sleep(self, seconds):
        self.calls.append(("sleep", seconds))

    def clear(self, **kwargs):
        self.calls.append(("clear", kwargs))

    def set_last(self, text):
        self.last_text = text

    def get_last(self):
        return self.last_text

    def remember_analysis(self, summary, **kwargs):
        self.analyses.append((summary, kwargs))

    def remember_text(self, lines, **kwargs):
        self.text_items.append((lines, kwargs))

    def selected_items(self, text, **_kwargs):
        if "produto" in str(text).lower():
            return ["Produto A - R$ 10,00"]
        return []

    def ask_model(self, *args, **kwargs):
        self.last_prompt = args[0]
        self.last_ask_kwargs = kwargs
        return self.ask_response


def make_runtime(deps: FakeBrowserTextRuntimeDeps) -> BrowserTextRuntime:
    return BrowserTextRuntime(
        activate_browser_window=deps.activate,
        activate_window_names=deps.activate_names,
        get_clipboard_text=deps.get_clipboard,
        set_clipboard_text=deps.set_clipboard,
        shortcut=deps.shortcut,
        tap=deps.tap,
        sleep=deps.sleep,
        clear_browser_snapshot=deps.clear,
        set_last_selected_text=deps.set_last,
        last_selected_text=deps.get_last,
        remember_browser_analysis=deps.remember_analysis,
        remember_text_items=deps.remember_text,
        selected_text_items=deps.selected_items,
        ask_model=deps.ask_model,
        vk_control=17,
        vk_c=67,
        vk_a=65,
        vk_escape=27,
    )


class BrowserTextRuntimeTests(unittest.TestCase):
    def test_reuses_reader_and_selection_commands(self):
        runtime = make_runtime(FakeBrowserTextRuntimeDeps())

        self.assertIs(runtime.text_reader(), runtime.text_reader())
        self.assertIs(runtime.selection_commands(), runtime.selection_commands())

    def test_read_selected_text_delegates_to_reader(self):
        deps = FakeBrowserTextRuntimeDeps()
        deps.clipboard_reads = ["old", "texto selecionado"]
        runtime = make_runtime(deps)

        result = runtime.read_selected_text()

        self.assertEqual(result, "texto selecionado")
        self.assertIn(("shortcut", (17, 67)), deps.calls)

    def test_read_selection_delegates_to_selection_commands(self):
        deps = FakeBrowserTextRuntimeDeps()
        deps.clipboard_reads = ["old", " texto selecionado "]
        runtime = make_runtime(deps)

        result = runtime.read_selection()

        self.assertEqual(result, "Texto selecionado: texto selecionado")
        self.assertEqual(deps.last_text, "texto selecionado")
        self.assertEqual(deps.analyses[0][1]["source"], "texto selecionado")

    def test_translate_selection_uses_model(self):
        deps = FakeBrowserTextRuntimeDeps()
        deps.clipboard_reads = ["old", "hello world"]
        runtime = make_runtime(deps)

        result = runtime.translate_selection()

        self.assertEqual(result, "Traduzi: ola mundo")
        self.assertIn("hello world", deps.last_prompt)
        self.assertEqual(deps.last_ask_kwargs["temperature"], 0.1)


if __name__ == "__main__":
    unittest.main()
