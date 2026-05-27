import unittest
from pathlib import Path

from core.cache_policy import (
    BRIEFING_CACHE_POLICY,
    INVESTMENT_REPORT_CACHE_POLICY,
    INVESTMENT_SUMMARY_CACHE_POLICY,
    VISION_SCREEN_CACHE_POLICY,
    cache_policy_for,
    is_cache_fresh,
)


class CachePolicyTests(unittest.TestCase):
    def test_known_cache_policies_have_expected_contracts(self):
        self.assertEqual(BRIEFING_CACHE_POLICY.path, Path("memory/briefing_cache.json"))
        self.assertEqual(BRIEFING_CACHE_POLICY.ttl_seconds, 15 * 60)
        self.assertEqual(INVESTMENT_SUMMARY_CACHE_POLICY.ttl_seconds, 10 * 60)
        self.assertEqual(INVESTMENT_REPORT_CACHE_POLICY.ttl_seconds, 10 * 60)
        self.assertTrue(VISION_SCREEN_CACHE_POLICY.requires_content_fingerprint)
        self.assertEqual(VISION_SCREEN_CACHE_POLICY.ttl_seconds, 90)

    def test_cache_policy_lookup_returns_registered_policy(self):
        self.assertIs(cache_policy_for("daily_briefing"), BRIEFING_CACHE_POLICY)
        self.assertIs(cache_policy_for("vision_screen"), VISION_SCREEN_CACHE_POLICY)

    def test_cache_policy_lookup_rejects_unknown_name(self):
        with self.assertRaises(ValueError):
            cache_policy_for("nao_existe")

    def test_is_cache_fresh_respects_ttl(self):
        self.assertTrue(is_cache_fresh(100, 60, now=150))
        self.assertTrue(is_cache_fresh("100", 60, now=160))
        self.assertFalse(is_cache_fresh(100, 60, now=161))
        self.assertFalse(is_cache_fresh(100, 0, now=100))
        self.assertFalse(is_cache_fresh("invalid", 60, now=100))


if __name__ == "__main__":
    unittest.main()
