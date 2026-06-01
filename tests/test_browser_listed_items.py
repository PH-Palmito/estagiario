import unittest

from tools.browser_listed_items import (
    BrowserListedItemCommands,
    click_browser_item_from_text,
    click_query_variants,
    extract_brl_price,
    short_click_query,
)


class FakeListedDeps:
    def __init__(self):
        self.active = True
        self.elements = []
        self.describe_calls = 0
        self.clicked_points = []
        self.clicked_texts = []
        self.page_clicks = []
        self.finds = []
        self.sleeps = []
        self.refreshes = 0
        self.click_text_result = False
        self.page_click_result = False

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

    def click_page(self, text):
        self.page_clicks.append(text)
        return self.page_click_result

    def click_text(self, text):
        self.clicked_texts.append(text)
        return self.click_text_result

    def find(self, query):
        self.finds.append(query)
        return "find"

    def click(self, x, y):
        self.clicked_points.append((x, y))

    def sleep(self, seconds):
        self.sleeps.append(seconds)


def make_commands(deps: FakeListedDeps) -> BrowserListedItemCommands:
    return BrowserListedItemCommands(
        activate_browser_window=deps.activate,
        refresh_browser_context=deps.refresh,
        listed_browser_elements=deps.listed,
        describe_screen=deps.describe,
        click_page_item_by_text=deps.click_page,
        click_browser_item_from_text=deps.click_text,
        browser_find=deps.find,
        click=deps.click,
        sleep=deps.sleep,
    )


class BrowserListedItemsTests(unittest.TestCase):
    def test_short_click_query_and_variants(self):
        self.assertEqual(short_click_query("Produto A R$ 10,00 detalhes"), "Produto A")
        self.assertEqual(short_click_query("um dois tres quatro cinco seis sete oito nove"), "um dois tres quatro cinco seis sete oito")
        self.assertIn("Produto A", click_query_variants("Produto A - R$ 10,00"))

    def test_click_browser_item_from_text_tries_variants(self):
        tried = []

        result = click_browser_item_from_text(
            "Notebook Gamer Lenovo Ideapad 16GB RTX 4060 R$ 4.999,00",
            lambda query: tried.append(query) or query == "Notebook Gamer Lenovo Ideapad 16GB RTX",
        )

        self.assertTrue(result)
        self.assertGreater(len(tried), 1)

    def test_extract_brl_price_returns_lowest_price(self):
        self.assertEqual(extract_brl_price("De R$ 1.999,90 por R$ 1.499,00"), 1499.0)
        self.assertIsNone(extract_brl_price("sem preco"))

    def test_click_listed_item_clicks_coordinates(self):
        deps = FakeListedDeps()
        deps.elements = [{"text": "Produto A", "x": 10, "y": 20}]

        result = make_commands(deps).click_listed_item(1)

        self.assertEqual(result, "Clicando no item 1: Produto A.")
        self.assertEqual(deps.clicked_points, [(10, 20)])
        self.assertEqual(deps.refreshes, 1)

    def test_click_listed_item_refreshes_list_when_index_missing(self):
        deps = FakeListedDeps()

        result = make_commands(deps).click_listed_item(1)

        self.assertEqual(result, "Li a tela, mas nao encontrei esse item na lista atual.")
        self.assertEqual(deps.describe_calls, 1)

    def test_click_listed_item_uses_text_fallback_and_find(self):
        deps = FakeListedDeps()
        deps.elements = [{"text": "Produto Super Longo R$ 10,00"}]

        result = make_commands(deps).click_listed_item(1)

        self.assertIn("Deixei ele procurado", result)
        self.assertEqual(deps.page_clicks, ["Produto Super Longo R$ 10,00"])
        self.assertEqual(deps.finds, ["Produto Super Longo"])
        self.assertEqual(deps.sleeps, [0.12])

    def test_click_listed_item_text_fallback_success(self):
        deps = FakeListedDeps()
        deps.elements = [{"text": "Produto B R$ 20,00"}]
        deps.click_text_result = True

        result = make_commands(deps).click_listed_item(1)

        self.assertEqual(result, "Clicando no item 1: Produto B R$ 20,00.")

    def test_describe_listed_item_and_cheapest(self):
        deps = FakeListedDeps()
        deps.elements = [
            {"text": "Produto caro R$ 20,00"},
            {"text": "Produto barato R$ 10,00"},
        ]
        commands = make_commands(deps)

        self.assertEqual(commands.describe_listed_item(2), "Item 2: Produto barato R$ 10,00.")
        self.assertEqual(commands.cheapest_listed_item(), "O mais barato que encontrei e o item 2: Produto barato R$ 10,00.")

    def test_invalid_indexes_and_no_prices(self):
        deps = FakeListedDeps()
        commands = make_commands(deps)

        self.assertEqual(commands.click_listed_item(0), "Qual item da lista?")
        self.assertEqual(commands.describe_listed_item(0), "Qual item?")
        deps.elements = [{"text": "Produto sem preco"}]
        self.assertEqual(commands.cheapest_listed_item(), "Ainda nao tenho precos claros na lista atual. Tente dizer: o que tem na tela.")


if __name__ == "__main__":
    unittest.main()
