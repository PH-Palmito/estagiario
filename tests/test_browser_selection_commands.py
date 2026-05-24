import unittest

from tools.browser_selection_commands import (
    BrowserSelectionCommands,
    build_translation_prompt,
    clean_translation_output,
)


class FakeSelectionDeps:
    def __init__(self):
        self.selected = " texto selecionado "
        self.last_text = ""
        self.clears = 0
        self.analyses = []
        self.text_items = []
        self.ask_response = "a traducao e: ola mundo"
        self.ask_error = None

    def read_selected(self, **kwargs):
        return self.selected

    def compact(self, text, max_length=650):
        compact = " ".join(str(text or "").split())
        if len(compact) <= max_length:
            return compact
        return compact[: max_length - 3].rstrip() + "..."

    def clear(self, **kwargs):
        self.clears += 1

    def set_last(self, text):
        self.last_text = text

    def get_last(self):
        return self.last_text

    def remember_analysis(self, summary, **kwargs):
        self.analyses.append((summary, kwargs))

    def remember_text(self, lines, **kwargs):
        self.text_items.append((lines, kwargs))

    def selected_items(self, text, **kwargs):
        if "produto" in text.lower():
            return ["Produto A - R$ 10,00"]
        return []

    def ask_model(self, *args, **kwargs):
        if self.ask_error:
            raise self.ask_error
        self.last_prompt = args[0]
        self.last_ask_kwargs = kwargs
        return self.ask_response


def make_commands(deps: FakeSelectionDeps) -> BrowserSelectionCommands:
    return BrowserSelectionCommands(
        read_selected_text_from_browser=deps.read_selected,
        compact_selected_text=deps.compact,
        clear_browser_snapshot=deps.clear,
        set_last_selected_text=deps.set_last,
        last_selected_text=deps.get_last,
        remember_browser_analysis=deps.remember_analysis,
        remember_text_items=deps.remember_text,
        selected_text_items=deps.selected_items,
        ask_model=deps.ask_model,
    )


class BrowserSelectionCommandsTests(unittest.TestCase):
    def test_clean_translation_output_removes_prefix_and_quotes(self):
        self.assertEqual(clean_translation_output('"A traducao e: ola mundo"'), "ola mundo")

    def test_build_translation_prompt_contains_target_and_text(self):
        prompt = build_translation_prompt("hello", target_language="portugues")

        self.assertIn("portugues", prompt)
        self.assertIn("hello", prompt)

    def test_read_selection_saves_last_text_and_analysis(self):
        deps = FakeSelectionDeps()

        result = make_commands(deps).read_selection()

        self.assertEqual(result, "Texto selecionado: texto selecionado")
        self.assertEqual(deps.last_text, "texto selecionado")
        self.assertEqual(deps.clears, 1)
        self.assertEqual(deps.analyses[0][1]["source"], "texto selecionado")

    def test_read_selection_handles_no_browser_and_empty_text(self):
        deps = FakeSelectionDeps()
        deps.selected = None
        self.assertIn("Nao encontrei", make_commands(deps).read_selection())

        deps = FakeSelectionDeps()
        deps.selected = "   "
        self.assertEqual(make_commands(deps).read_selection(), "Nao encontrei texto selecionado.")
        self.assertEqual(deps.last_text, "")

    def test_translate_selection_uses_model_and_cleans_output(self):
        deps = FakeSelectionDeps()

        result = make_commands(deps).translate_selection()

        self.assertEqual(result, "Traduzi: ola mundo")
        self.assertIn("texto selecionado", deps.last_prompt)
        self.assertEqual(deps.last_ask_kwargs["temperature"], 0.1)

    def test_translate_last_selection_requires_saved_text(self):
        deps = FakeSelectionDeps()
        self.assertIn("Ainda nao tenho", make_commands(deps).translate_last_selection())

        deps.last_text = "hello"
        self.assertEqual(make_commands(deps).translate_last_selection(), "Traduzi: ola mundo")

    def test_translate_handles_model_error_and_empty_output(self):
        deps = FakeSelectionDeps()
        deps.ask_error = RuntimeError("offline")
        self.assertIn("Nao consegui traduzir", make_commands(deps).translate_selection())

        deps = FakeSelectionDeps()
        deps.ask_response = "   "
        self.assertEqual(make_commands(deps).translate_selection(), "Nao consegui gerar a traducao.")

    def test_read_selected_products_saves_items(self):
        deps = FakeSelectionDeps()
        deps.selected = "produto selecionado"

        result = make_commands(deps).read_selected_products()

        self.assertEqual(result, "Li selecionado: 1. Produto A - R$ 10,00")
        self.assertEqual(deps.text_items[0][0], ["Produto A - R$ 10,00"])


if __name__ == "__main__":
    unittest.main()
