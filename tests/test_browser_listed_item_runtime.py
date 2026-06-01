import unittest

from tools.browser_listed_item_runtime import BrowserListedItemRuntime


class FakeBrowserListedItemRuntimeDeps:
    def __init__(self):
        self.active = True
        self.elements = []
        self.describe_calls = 0
        self.clicked_points = []
        self.clicked_texts = []
        self.finds = []
        self.refreshes = 0
        self.click_text_result = False

    def activate(self):
        return self.active

    def refresh(self):
        self.refreshes += 1
        return "ctx"

    def listed(self):
        return list(self.elements)

    def describe(self):
        self.describe_calls += 1
        return "descrito"

    def click_page(self, _text):
        return False

    def click_text(self, text):
        self.clicked_texts.append(text)
        return self.click_text_result

    def find(self, query):
        self.finds.append(query)
        return "find"

    def click(self, x, y):
        self.clicked_points.append((x, y))


def make_runtime(deps: FakeBrowserListedItemRuntimeDeps) -> BrowserListedItemRuntime:
    return BrowserListedItemRuntime(
        activate_browser_window=deps.activate,
        refresh_browser_context=deps.refresh,
        listed_browser_elements=deps.listed,
        describe_screen=deps.describe,
        click_page_item_by_text=deps.click_page,
        click_browser_element_by_text=deps.click_text,
        browser_find=deps.find,
        click=deps.click,
        sleep=lambda _seconds: None,
    )


class BrowserListedItemRuntimeTests(unittest.TestCase):
    def test_reuses_commands_instance(self):
        runtime = make_runtime(FakeBrowserListedItemRuntimeDeps())

        self.assertIs(runtime.commands(), runtime.commands())

    def test_click_browser_item_from_text_tries_variants(self):
        deps = FakeBrowserListedItemRuntimeDeps()
        deps.click_text_result = True
        runtime = make_runtime(deps)

        self.assertTrue(runtime.click_browser_item_from_text("Notebook Gamer R$ 4.999,00"))
        self.assertEqual(deps.clicked_texts[0], "Notebook Gamer")

    def test_click_listed_item_delegates_to_commands(self):
        deps = FakeBrowserListedItemRuntimeDeps()
        deps.elements = [{"text": "Produto A", "x": 10, "y": 20}]
        runtime = make_runtime(deps)

        result = runtime.click_listed_item(1)

        self.assertEqual(result, "Clicando no item 1: Produto A.")
        self.assertEqual(deps.clicked_points, [(10, 20)])
        self.assertEqual(deps.refreshes, 1)

    def test_describe_and_cheapest_delegate_to_commands(self):
        deps = FakeBrowserListedItemRuntimeDeps()
        deps.elements = [
            {"text": "Produto caro R$ 20,00"},
            {"text": "Produto barato R$ 10,00"},
        ]
        runtime = make_runtime(deps)

        self.assertEqual(runtime.describe_listed_item(2), "Item 2: Produto barato R$ 10,00.")
        self.assertEqual(runtime.cheapest_listed_item(), "O mais barato que encontrei e o item 2: Produto barato R$ 10,00.")


if __name__ == "__main__":
    unittest.main()
