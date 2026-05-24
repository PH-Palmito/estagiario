import unittest

from tools.browser_screen_analysis import (
    content_showcase,
    detect_screen_category,
    extract_finance_focus_lines,
    extract_finance_metrics,
    merge_screen_lines,
    screen_lines_quality,
    trim_detail_text,
)


class BrowserScreenAnalysisTests(unittest.TestCase):
    def test_detects_categories_from_url_and_text(self):
        self.assertEqual(detect_screen_category([], page_url="https://github.com/openai/codex"), "repositorio github")
        self.assertEqual(detect_screen_category([], page_url="https://www.youtube.com/watch?v=1"), "video youtube")
        self.assertEqual(detect_screen_category(["Patrimonio R$ 1.000,00"]), "financas")
        self.assertEqual(detect_screen_category(["Smartphone Galaxy 128 GB"]), "smartphones")

    def test_extract_finance_metrics_pairs_labels_and_values(self):
        result = extract_finance_metrics(["Patrimonio", "R$ 8.409,14", "Rentabilidade 15,57%"])

        self.assertIn("Patrimonio: R$ 8.409,14", result)
        self.assertIn("Rentabilidade 15,57%", result)

    def test_extract_finance_focus_lines_prioritizes_money_and_labels(self):
        result = extract_finance_focus_lines(["menu", "Patrimonio R$ 8.409,14", "Dividendos 20/05"], limit=2)

        self.assertEqual(result, ["Patrimonio R$ 8.409,14", "Dividendos 20/05"])

    def test_merge_screen_lines_deduplicates_and_keeps_order(self):
        result = merge_screen_lines([" A ", "B"], ["a", "C"], limit=3)

        self.assertEqual(result, ["A", "B", "C"])

    def test_quality_showcase_and_trim(self):
        self.assertGreater(screen_lines_quality(["Notebook Lenovo com 16 GB de RAM"]), 0)
        self.assertEqual(content_showcase([" um ", " dois ", " um "], limit=2), ["um", "dois"])
        self.assertEqual(trim_detail_text("abcdef", max_length=5), "ab...")


if __name__ == "__main__":
    unittest.main()
