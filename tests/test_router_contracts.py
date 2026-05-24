import unittest

from core.router import DETECTOR_GROUPS, iter_detectors

ROUTE_CONTRACTS = [
    ("remova BBAS3 da watchlist", "investment_strategy", "investment_remove_watchlist"),
    ("delete o arquivo relatorio.txt", "files", "delete_file"),
    ("noticias da carteira", "investment_questions", "investment_memory_answer"),
    ("qual a cotacao de BBAS3", "investment_questions", "investment_memory_answer"),
    ("toque bohemian rhapsody no spotify", "fast_path", "browser_search_music"),
    ("nova aba", "browser", "browser_new_tab"),
    ("analise o codigo", "code", "code_inspect_workspace"),
    ("analisar grafico", "image", "image_analyze_screen_graph"),
    ("status da visao", "vision", "vision_status"),
    ("abrir investidor 10", "investment_browser", "browser_open_wallet_and_summarize"),
]


def _first_detector_match(phrase: str):
    for group_name, detector in iter_detectors():
        result = detector(phrase)
        if result:
            return group_name, detector.__name__, result
    return None, None, None


class RouterContractTests(unittest.TestCase):
    def test_detector_groups_are_named_and_populated(self):
        group_names = [name for name, detectors in DETECTOR_GROUPS]
        self.assertEqual(len(group_names), len(set(group_names)))

        for group_name, detectors in DETECTOR_GROUPS:
            with self.subTest(group=group_name):
                self.assertTrue(detectors)
                self.assertTrue(all(callable(detector) for detector in detectors))

    def test_priority_sensitive_phrases_route_to_expected_domain(self):
        for phrase, expected_group, expected_intent in ROUTE_CONTRACTS:
            with self.subTest(phrase=phrase):
                group_name, detector_name, result = _first_detector_match(phrase)

                self.assertIsNotNone(result, f"No detector matched {phrase!r}")
                self.assertEqual(group_name, expected_group, detector_name)
                self.assertEqual(result.get("intent"), expected_intent)
