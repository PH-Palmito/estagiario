import unittest
from types import SimpleNamespace

from tools.browser_ui_automation import (
    BrowserUiAutomation,
    normalize_ui_text,
    parse_browser_items_output,
    parse_point_output,
)


class FakeBrowserUiDeps:
    def __init__(self):
        self.stdout = ""
        self.error = None
        self.commands = []
        self.clicks = []

    def run_powershell(self, script, **kwargs):
        if self.error:
            raise self.error
        self.commands.append((script, kwargs))
        return SimpleNamespace(stdout=self.stdout, returncode=0)

    def click(self, x, y):
        self.clicks.append((x, y))


def make_ui(deps: FakeBrowserUiDeps) -> BrowserUiAutomation:
    return BrowserUiAutomation(
        browser_names=["chrome", "msedge"],
        run_powershell=deps.run_powershell,
        click=deps.click,
    )


class BrowserUiAutomationTests(unittest.TestCase):
    def test_normalize_ui_text_and_parse_point(self):
        self.assertEqual(normalize_ui_text("Olá, Mundo!"), "ola mundo")
        self.assertEqual(parse_point_output("__POINT__:10,20"), (10, 20))
        self.assertIsNone(parse_point_output("__NO_MATCH__"))

    def test_parse_browser_items_output(self):
        output = "\n".join(
            [
                "__ITEM__|Produto A|10|20|Hyperlink",
                "__ITEM__|Produto B|x|30|Button",
                "noise",
                "__ITEM__|Produto C|40|50|Text",
            ]
        )

        self.assertEqual(
            parse_browser_items_output(output, limit=2),
            [
                {"text": "Produto A", "x": 10, "y": 20, "type": "Hyperlink"},
                {"text": "Produto C", "x": 40, "y": 50, "type": "Text"},
            ],
        )
        self.assertIsNone(parse_browser_items_output("__NO_BROWSER__"))

    def test_click_first_browser_link_clicks_point(self):
        deps = FakeBrowserUiDeps()
        deps.stdout = "__POINT__:100,200"

        self.assertTrue(make_ui(deps).click_first_browser_link())
        self.assertIn("'chrome'", deps.commands[0][0])
        self.assertEqual(deps.commands[0][1]["timeout_seconds"], 8)
        self.assertEqual(deps.clicks, [(100, 200)])

    def test_click_browser_element_by_text_injects_query_words(self):
        deps = FakeBrowserUiDeps()
        deps.stdout = "__POINT__:30,40"

        self.assertTrue(make_ui(deps).click_browser_element_by_text("Olá Produto", app_names=["brave"]))
        script = deps.commands[0][0]
        self.assertIn("'brave'", script)
        self.assertIn("'ola'", script)
        self.assertIn("'produto'", script)
        self.assertEqual(deps.clicks, [(30, 40)])

    def test_click_methods_return_false_without_point_or_on_error(self):
        deps = FakeBrowserUiDeps()
        deps.stdout = "__NO_LINK__"
        self.assertFalse(make_ui(deps).click_first_browser_link())

        deps = FakeBrowserUiDeps()
        deps.error = RuntimeError("boom")
        self.assertFalse(make_ui(deps).click_browser_element_by_text("produto"))

    def test_read_browser_elements_uses_parser(self):
        deps = FakeBrowserUiDeps()
        deps.stdout = "__ITEM__|Produto A|10|20|Hyperlink"

        self.assertEqual(
            make_ui(deps).read_browser_elements(limit=1),
            [{"text": "Produto A", "x": 10, "y": 20, "type": "Hyperlink"}],
        )


if __name__ == "__main__":
    unittest.main()
