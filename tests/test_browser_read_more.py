import unittest

from tools.browser_read_more import browser_read_more


class BrowserReadMoreTests(unittest.TestCase):
    def test_requires_active_browser(self):
        result = browser_read_more(
            activate_browser_window=lambda: False,
            mouse_wheel=lambda _delta: None,
            describe_screen=lambda: "nao usado",
            sleep=lambda _seconds: None,
        )

        self.assertEqual(result, "Nao encontrei um navegador aberto para ler mais.")

    def test_scrolls_and_rephrases_visible_screen(self):
        calls = []

        result = browser_read_more(
            activate_browser_window=lambda: True,
            mouse_wheel=lambda delta: calls.append(("wheel", delta)),
            describe_screen=lambda: "Vejo na tela: 1. Item",
            sleep=lambda seconds: calls.append(("sleep", seconds)),
        )

        self.assertEqual(result, "Mais abaixo vejo: 1. Item")
        self.assertEqual(calls, [("wheel", -550), ("sleep", 0.25)])

    def test_rephrases_page_text(self):
        result = browser_read_more(
            activate_browser_window=lambda: True,
            mouse_wheel=lambda _delta: None,
            describe_screen=lambda: "Consegui ler texto da pagina: Linha A",
            sleep=lambda _seconds: None,
        )

        self.assertEqual(result, "Mais abaixo consegui ler: Linha A")

    def test_returns_other_result_unchanged(self):
        result = browser_read_more(
            activate_browser_window=lambda: True,
            mouse_wheel=lambda _delta: None,
            describe_screen=lambda: "Nao consegui ler a tela.",
            sleep=lambda _seconds: None,
        )

        self.assertEqual(result, "Nao consegui ler a tela.")


if __name__ == "__main__":
    unittest.main()
