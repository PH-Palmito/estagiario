import unittest

from core.router import DETECTOR_GROUPS, ROUTER_GROUPS, iter_detectors, route, route_match, route_trace
from core.router_registry import (
    INTENT_LEVEL_COMPOSITE_TASK,
    INTENT_LEVEL_CONVERSATION,
    INTENT_LEVEL_DIRECT_COMMAND,
    INTENT_LEVEL_QUESTION,
)

ROUTE_CONTRACTS = [
    ("remova BBAS3 da watchlist", "investment_strategy", "investment_remove_watchlist"),
    ("delete o arquivo relatorio.txt", "files", "delete_file"),
    ("noticias da carteira", "investment_questions", "investment_memory_answer"),
    ("qual a cotacao de BBAS3", "investment_questions", "investment_memory_answer"),
    ("como o el nino afeta meus investimentos", "investment_questions", "investment_memory_answer"),
    ("como o el nino afeta o VGIA11?", "investment_questions", "investment_memory_answer"),
    ("e o vgia como é afetado?", "investment_questions", "investment_memory_answer"),
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
    def test_router_groups_have_explicit_priority_order(self):
        priorities = [group.priority for group in ROUTER_GROUPS]
        self.assertEqual(priorities, list(range(len(ROUTER_GROUPS))))
        self.assertEqual(
            [name for name, _detectors in DETECTOR_GROUPS],
            [group.name for group in ROUTER_GROUPS],
        )

    def test_detector_groups_are_named_and_populated(self):
        group_names = [name for name, detectors in DETECTOR_GROUPS]
        self.assertEqual(len(group_names), len(set(group_names)))

        for group_name, detectors in DETECTOR_GROUPS:
            with self.subTest(group=group_name):
                self.assertTrue(detectors)
                self.assertTrue(all(callable(detector) for detector in detectors))

    def test_router_groups_expose_intent_levels(self):
        levels = {group.name: group.intent_level for group in ROUTER_GROUPS}

        self.assertEqual(levels["browser"], INTENT_LEVEL_DIRECT_COMMAND)
        self.assertEqual(levels["investment_questions"], INTENT_LEVEL_QUESTION)
        self.assertEqual(levels["macros"], INTENT_LEVEL_COMPOSITE_TASK)
        self.assertEqual(levels["conversation"], INTENT_LEVEL_CONVERSATION)

    def test_priority_sensitive_phrases_route_to_expected_domain(self):
        for phrase, expected_group, expected_intent in ROUTE_CONTRACTS:
            with self.subTest(phrase=phrase):
                group_name, detector_name, result = _first_detector_match(phrase)

                self.assertIsNotNone(result, f"No detector matched {phrase!r}")
                self.assertEqual(group_name, expected_group, detector_name)
                self.assertEqual(result.get("intent"), expected_intent)

    def test_route_match_exposes_detector_metadata_without_changing_route_result(self):
        match = route_match("nova aba")

        self.assertIsNotNone(match)
        self.assertEqual(match.group_name, "browser")
        self.assertEqual(match.intent_level, INTENT_LEVEL_DIRECT_COMMAND)
        self.assertTrue(match.detector_name)
        self.assertEqual(match.result, route("nova aba"))

    def test_route_trace_exposes_checked_groups(self):
        trace = route_trace("nova aba")

        self.assertIsNotNone(trace.match)
        self.assertEqual(trace.match.result, route("nova aba"))
        self.assertIn("fast_path", trace.checked_groups)
        self.assertIn("browser", trace.checked_groups)
