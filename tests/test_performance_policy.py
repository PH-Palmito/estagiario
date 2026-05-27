import unittest

from core.performance_policy import action_performance_advice, default_action_performance_advice


class PerformancePolicyTests(unittest.TestCase):
    def test_fast_action_stays_foreground(self):
        advice = action_performance_advice("open_app", avg_ms=120, max_ms=240, count=3)

        self.assertEqual(advice.mode, "foreground_ok")
        self.assertFalse(advice.should_background)
        self.assertFalse(advice.should_cache)

    def test_known_heavy_action_uses_background_and_cache(self):
        advice = action_performance_advice("daily_briefing", avg_ms=800, max_ms=900, count=1)

        self.assertEqual(advice.mode, "background_with_cache")
        self.assertTrue(advice.should_background)
        self.assertTrue(advice.should_cache)

    def test_default_advice_marks_known_heavy_action_before_metrics(self):
        advice = default_action_performance_advice("image_analyze_screen")

        self.assertEqual(advice.mode, "background_with_cache")
        self.assertTrue(advice.should_background)
        self.assertTrue(advice.should_cache)

    def test_investment_report_uses_background_and_cache(self):
        advice = default_action_performance_advice("investment_financial_report")

        self.assertEqual(advice.mode, "background_with_cache")
        self.assertTrue(advice.should_background)
        self.assertTrue(advice.should_cache)

    def test_slow_unknown_action_becomes_background_candidate(self):
        advice = action_performance_advice("custom_report", avg_ms=700, max_ms=2600, count=1)

        self.assertEqual(advice.mode, "background_candidate")
        self.assertTrue(advice.should_background)
        self.assertFalse(advice.should_cache)

    def test_repeated_mid_cost_action_becomes_cache_candidate(self):
        advice = action_performance_advice("search_notes", avg_ms=950, max_ms=980, count=3)

        self.assertEqual(advice.mode, "cache_candidate")
        self.assertFalse(advice.should_background)
        self.assertTrue(advice.should_cache)


if __name__ == "__main__":
    unittest.main()
