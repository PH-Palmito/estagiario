import unittest

from tools.browser_screen_narrative import (
    clean_browser_title,
    explain_screen_lines,
    investment_screen_summary,
    items_are_navigation_heavy,
    parse_github_repo_from_url,
    should_auto_summarize,
    summarize_screen_lines,
)


class BrowserScreenNarrativeTests(unittest.TestCase):
    def test_clean_browser_title_removes_browser_suffix(self):
        self.assertEqual(clean_browser_title("GitHub - openai/codex - Google Chrome"), "GitHub - openai/codex")

    def test_parse_github_repo_from_url(self):
        self.assertEqual(parse_github_repo_from_url("https://github.com/openai/codex/issues"), "openai/codex")
        self.assertEqual(parse_github_repo_from_url("https://example.com/openai/codex"), "")

    def test_summarizes_github_repository_from_title_and_lines(self):
        result = summarize_screen_lines(
            ["Repository navigation", "README", "AI coding agent that runs locally"],
            page_url="https://github.com/openai/codex",
            page_title="GitHub - openai/codex: AI coding agent",
        )

        self.assertIn("repositorio openai/codex", result)
        self.assertIn("AI coding agent", result)

    def test_explains_news_with_visible_focus(self):
        result = explain_screen_lines(
            ["Publicado hoje", "Empresa anuncia investimento bilionario em IA para novos produtos"],
            page_url="https://g1.globo.com/tecnologia/noticia/teste",
            page_title="Empresa anuncia investimento bilionario em IA - Google Chrome",
        )

        self.assertIn("noticia", result)
        self.assertIn("investimento", result)

    def test_investment_summary_pairs_metrics(self):
        result = investment_screen_summary(
            ["Patrimonio", "R$ 8.409,14", "Rentabilidade 15,57%"],
            page_url="https://investidor10.com.br/carteira",
            page_title="Carteira Investidor10",
        )

        self.assertIn("Resumo financeiro da tela", result)
        self.assertIn("Patrimonio: R$ 8.409,14", result)
        self.assertIn("Rentabilidade 15,57%", result)

    def test_auto_summary_and_navigation_detection(self):
        self.assertTrue(should_auto_summarize(["Patrimonio R$ 8.409,14"], 5, page_url="https://investidor10.com.br"))
        self.assertTrue(items_are_navigation_heavy(["Repository navigation", "Pull requests"], page_url="https://github.com/openai/codex"))


if __name__ == "__main__":
    unittest.main()
