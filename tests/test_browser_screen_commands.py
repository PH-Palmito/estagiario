import unittest

from tools.browser_screen_commands import BrowserScreenCommands


class FakeScreenCommandDeps:
    def __init__(self):
        self.active = True
        self.context = "ctx"
        self.url = "https://example.com"
        self.title = "Pagina teste"
        self.capture = {
            "items": [],
            "combined_lines": ["Notebook Lenovo com 16 GB de RAM"],
            "combined_quality": 40,
            "prefer_page_text": False,
        }
        self.cleared = []
        self.elements = []
        self.text_items = []
        self.analyses = []
        self.snapshots = []

    def activate(self):
        return self.active

    def refresh(self):
        return self.context

    def get_url(self):
        return self.url

    def get_title(self):
        return self.title

    def read_capture(self, **kwargs):
        self.last_capture_kwargs = kwargs
        return self.capture

    def clear(self, **kwargs):
        self.cleared.append(kwargs)

    def set_elements(self, elements, **kwargs):
        self.elements.append((elements, kwargs))

    def remember_text(self, lines, **kwargs):
        self.text_items.append((lines, kwargs))

    def remember_analysis(self, summary, **kwargs):
        self.analyses.append((summary, kwargs))

    def intro(self):
        return "Resumo da tela"

    def save_snapshot(self, **kwargs):
        self.snapshots.append(kwargs)


def make_commands(deps: FakeScreenCommandDeps) -> BrowserScreenCommands:
    return BrowserScreenCommands(
        activate_browser_window=deps.activate,
        refresh_browser_context=deps.refresh,
        get_browser_url=deps.get_url,
        get_page_title=deps.get_title,
        read_screen_content_lines=deps.read_capture,
        clear_browser_snapshot=deps.clear,
        set_browser_elements=deps.set_elements,
        remember_text_items=deps.remember_text,
        remember_browser_analysis=deps.remember_analysis,
        screen_summary_intro=deps.intro,
        save_investment_snapshot=deps.save_snapshot,
    )


class BrowserScreenCommandsTests(unittest.TestCase):
    def test_summarize_screen_remembers_text_lines(self):
        deps = FakeScreenCommandDeps()
        result = make_commands(deps).summarize_screen()

        self.assertTrue(result.startswith("Resumo da tela:"))
        self.assertEqual(deps.last_capture_kwargs["item_limit"], 10)
        self.assertEqual(deps.text_items[0][0], deps.capture["combined_lines"])
        self.assertEqual(deps.analyses[0][0], result)

    def test_explain_screen_remembers_browser_elements(self):
        deps = FakeScreenCommandDeps()
        deps.capture["items"] = [{"text": "Item clicavel"}]

        result = make_commands(deps).explain_screen()

        self.assertTrue(result.startswith("Detalhando a tela:"))
        self.assertEqual(deps.last_capture_kwargs["item_limit"], 12)
        self.assertEqual(deps.elements[0][0], deps.capture["items"])

    def test_investment_snapshot_saves_metrics_and_analysis(self):
        deps = FakeScreenCommandDeps()
        deps.url = "https://investidor10.com.br/carteira"
        deps.capture["combined_lines"] = ["Patrimonio", "R$ 8.409,14", "Rentabilidade 15,57%"]

        result = make_commands(deps).investment_snapshot()

        self.assertIn("Resumo financeiro da tela", result)
        self.assertEqual(deps.last_capture_kwargs["page_limit"], 30)
        self.assertIn("Patrimonio: R$ 8.409,14", deps.snapshots[0]["metrics"])
        self.assertEqual(deps.analyses[0][1]["source"], "pagina financeira")

    def test_describe_screen_returns_clickable_list_for_good_items(self):
        deps = FakeScreenCommandDeps()
        deps.capture = {
            "items": [{"text": "Botao principal"}],
            "combined_lines": ["Botao principal"],
            "combined_quality": 40,
            "prefer_page_text": False,
        }

        result = make_commands(deps).describe_screen()

        self.assertIn("Vejo na tela: 1. Botao principal", result)

    def test_empty_capture_clears_context(self):
        deps = FakeScreenCommandDeps()
        deps.capture["combined_lines"] = []

        result = make_commands(deps).summarize_screen()

        self.assertEqual(result, "Nao consegui resumir a tela atual.")
        self.assertEqual(deps.cleared, [{"context": "ctx"}])

    def test_inactive_browser_returns_specific_message(self):
        deps = FakeScreenCommandDeps()
        deps.active = False

        self.assertIn("Nao encontrei", make_commands(deps).describe_screen())


if __name__ == "__main__":
    unittest.main()
