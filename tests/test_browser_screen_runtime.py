import unittest

from tools.browser_screen_runtime import BrowserScreenRuntime


class FakeBrowserScreenRuntimeDeps:
    def __init__(self):
        self.clipboard = "old"
        self.clipboard_reads = []
        self.shortcuts = []
        self.taps = []
        self.set_values = []
        self.context = "ctx"
        self.title = ""
        self.elements = [{"text": "Botao principal"}]
        self.cleared = []
        self.saved_elements = []
        self.text_items = []
        self.analyses = []

    def activate(self):
        return True

    def refresh(self):
        return self.context

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

    def context_changed(self, *_args):
        return False

    def get_title(self):
        return self.title

    def clean_title(self, title):
        return title.replace(" - Google Chrome", "")

    def clear(self, **kwargs):
        self.cleared.append(kwargs)

    def set_elements(self, elements, **kwargs):
        self.saved_elements.append((elements, kwargs))

    def remember_text(self, lines, **kwargs):
        self.text_items.append((lines, kwargs))

    def remember_analysis(self, summary, **kwargs):
        self.analyses.append((summary, kwargs))

    def save_snapshot(self, **kwargs):
        self.snapshot = kwargs


def make_runtime(deps: FakeBrowserScreenRuntimeDeps) -> BrowserScreenRuntime:
    return BrowserScreenRuntime(
        activate_browser_window=deps.activate,
        refresh_browser_context=deps.refresh,
        get_clipboard_text=deps.get_clipboard,
        set_clipboard_text=deps.set_clipboard,
        shortcut=deps.shortcut,
        tap=deps.tap,
        read_browser_elements=deps.read_elements,
        browser_context_recently_changed=deps.context_changed,
        get_foreground_window_title=deps.get_title,
        clean_browser_title=deps.clean_title,
        clear_browser_snapshot=deps.clear,
        set_browser_elements=deps.set_elements,
        remember_text_items=deps.remember_text,
        remember_browser_analysis=deps.remember_analysis,
        save_investment_snapshot=deps.save_snapshot,
        vk_control=1,
        vk_a=65,
        vk_c=67,
        vk_escape=27,
        vk_l=76,
        sleep=lambda _seconds: None,
        random_choice=lambda intros: intros[0],
    )


class BrowserScreenRuntimeTests(unittest.TestCase):
    def test_reuses_capture_and_commands_instances(self):
        runtime = make_runtime(FakeBrowserScreenRuntimeDeps())

        self.assertIs(runtime.screen_capture(), runtime.screen_capture())
        self.assertIs(runtime.screen_commands(), runtime.screen_commands())

    def test_get_browser_url_delegates_to_capture(self):
        deps = FakeBrowserScreenRuntimeDeps()
        deps.clipboard_reads = ["old", "https://example.com/page"]
        runtime = make_runtime(deps)

        result = runtime.get_browser_url()

        self.assertEqual(result, "https://example.com/page")
        self.assertIn((1, 76), deps.shortcuts)
        self.assertIn((1, 67), deps.shortcuts)
        self.assertEqual(deps.taps, [27])

    def test_describe_screen_delegates_to_screen_commands(self):
        deps = FakeBrowserScreenRuntimeDeps()
        runtime = make_runtime(deps)

        result = runtime.describe_screen()

        self.assertIn("Botao principal", result)
        self.assertEqual(deps.saved_elements[0][0], deps.elements)
        self.assertEqual(deps.analyses[0][0], result)

    def test_screen_summary_intro_uses_configured_choice(self):
        runtime = make_runtime(FakeBrowserScreenRuntimeDeps())

        self.assertEqual(runtime.screen_summary_intro(), "Resumo da tela")


if __name__ == "__main__":
    unittest.main()
