import unittest

from core.toolsets import format_relevant_toolsets, format_toolset_catalog, list_toolsets, select_toolsets


class ToolsetsTests(unittest.TestCase):
    def test_list_toolsets_contains_expected_modes(self):
        names = {item["name"] for item in list_toolsets()}

        self.assertIn("voz_rapida", names)
        self.assertIn("programacao", names)
        self.assertIn("carteira", names)
        self.assertIn("navegador", names)
        self.assertIn("sistema", names)
        self.assertIn("pesquisa", names)

    def test_select_toolsets_scores_relevant_mode(self):
        matches = select_toolsets("rodar teste e revisar codigo")

        self.assertEqual(matches[0]["name"], "programacao")

    def test_format_catalog_and_relevant_toolsets(self):
        self.assertIn("Toolsets do Axel", format_toolset_catalog())
        self.assertIn("Programacao", format_relevant_toolsets("bug no codigo"))


if __name__ == "__main__":
    unittest.main()
