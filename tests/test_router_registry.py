import unittest

from core.router_registry import (
    INTENT_LEVEL_COMPOSITE_TASK,
    INTENT_LEVEL_DIRECT_COMMAND,
    build_detector_groups,
    detector_group_tuples,
    find_detector_match,
    iter_group_detectors,
    trace_route,
)


def no_match(_text):
    return None


def match_echo(text):
    return {"intent": "echo", "target": text}


class RouterRegistryTests(unittest.TestCase):
    def test_build_detector_groups_assigns_priority(self):
        groups = build_detector_groups(
            [
                ("first", [no_match]),
                ("second", [match_echo]),
            ]
        )

        self.assertEqual([group.priority for group in groups], [0, 1])
        self.assertEqual([group.intent_level for group in groups], [INTENT_LEVEL_DIRECT_COMMAND, INTENT_LEVEL_DIRECT_COMMAND])
        self.assertEqual(detector_group_tuples(groups)[0][0], "first")

    def test_build_detector_groups_accepts_intent_level(self):
        groups = build_detector_groups(
            [
                ("routine", [match_echo], INTENT_LEVEL_COMPOSITE_TASK),
            ]
        )

        self.assertEqual(groups[0].intent_level, INTENT_LEVEL_COMPOSITE_TASK)

    def test_iter_group_detectors_preserves_order(self):
        groups = build_detector_groups(
            [
                ("first", [no_match]),
                ("second", [match_echo]),
            ]
        )

        ordered = [(name, detector.__name__) for name, detector in iter_group_detectors(groups)]

        self.assertEqual(ordered, [("first", "no_match"), ("second", "match_echo")])

    def test_find_detector_match_returns_metadata(self):
        groups = build_detector_groups(
            [
                ("first", [no_match]),
                ("second", [match_echo]),
            ]
        )

        match = find_detector_match("teste", groups)

        self.assertIsNotNone(match)
        self.assertEqual(match.group_name, "second")
        self.assertEqual(match.detector_name, "match_echo")
        self.assertEqual(match.result, {"intent": "echo", "target": "teste"})
        self.assertEqual(match.intent_level, INTENT_LEVEL_DIRECT_COMMAND)

    def test_trace_route_counts_checked_detectors(self):
        groups = build_detector_groups(
            [
                ("first", [no_match]),
                ("second", [match_echo]),
            ]
        )

        trace = trace_route("teste", groups)

        self.assertEqual(trace.checked_detectors, 2)
        self.assertEqual(trace.checked_groups, ("first", "second"))
        self.assertEqual(trace.match.group_name, "second")
        self.assertEqual(trace.match.intent_level, INTENT_LEVEL_DIRECT_COMMAND)

    def test_trace_route_reports_no_match(self):
        groups = build_detector_groups([("first", [no_match])])

        trace = trace_route("teste", groups)

        self.assertIsNone(trace.match)
        self.assertEqual(trace.checked_detectors, 1)


if __name__ == "__main__":
    unittest.main()
