import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import investment_tools


class InvestmentCacheTests(unittest.TestCase):
    def test_investment_summary_reuses_fresh_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "investment_summary_cache.json"
            calls = []

            with (
                patch.object(investment_tools, "INVESTMENT_SUMMARY_CACHE_PATH", cache_path),
                patch.object(investment_tools.time, "time", return_value=1000),
                patch.object(
                    investment_tools,
                    "_build_investment_memory_summary",
                    side_effect=lambda: calls.append("build") or "Resumo novo",
                ),
            ):
                first = investment_tools.investment_memory_summary()
                second = investment_tools.investment_memory_summary()

        self.assertEqual(first, "Resumo novo")
        self.assertEqual(second, "Resumo novo")
        self.assertEqual(calls, ["build"])

    def test_investment_report_refreshes_expired_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "investment_report_cache.json"
            cache_path.write_text(json.dumps({"created_at": 0, "text": "velho"}), encoding="utf-8")

            with (
                patch.object(investment_tools, "INVESTMENT_REPORT_CACHE_PATH", cache_path),
                patch.object(investment_tools.time, "time", return_value=1000),
                patch.object(investment_tools, "_build_investment_financial_report", return_value="novo"),
            ):
                result = investment_tools.investment_financial_report(ttl_seconds=10)

        self.assertEqual(result, "novo")

    def test_investment_report_can_bypass_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "investment_report_cache.json"
            cache_path.write_text(json.dumps({"created_at": 1000, "text": "cache"}), encoding="utf-8")

            with (
                patch.object(investment_tools, "INVESTMENT_REPORT_CACHE_PATH", cache_path),
                patch.object(investment_tools, "_build_investment_financial_report", return_value="direto"),
            ):
                result = investment_tools.investment_financial_report(use_cache=False)

        self.assertEqual(result, "direto")

    def test_invalid_investment_cache_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "investment_summary_cache.json"
            cache_path.write_text("{invalid", encoding="utf-8")

            with (
                patch.object(investment_tools, "INVESTMENT_SUMMARY_CACHE_PATH", cache_path),
                patch.object(investment_tools, "_build_investment_memory_summary", return_value="recuperado"),
            ):
                result = investment_tools.investment_memory_summary()

        self.assertEqual(result, "recuperado")

    def test_refresh_public_wallet_clears_investment_caches(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary_path = Path(temp_dir) / "investment_summary_cache.json"
            report_path = Path(temp_dir) / "investment_report_cache.json"
            summary_path.write_text("{}", encoding="utf-8")
            report_path.write_text("{}", encoding="utf-8")

            with (
                patch.object(investment_tools, "INVESTMENT_SUMMARY_CACHE_PATH", summary_path),
                patch.object(investment_tools, "INVESTMENT_REPORT_CACHE_PATH", report_path),
                patch.object(
                    investment_tools,
                    "refresh_wallet_snapshot_auto",
                    return_value={"summary": "Carteira atualizada"},
                ),
            ):
                result = investment_tools.investment_refresh_public_wallet()

        self.assertEqual(result, "Carteira atualizada")
        self.assertFalse(summary_path.exists())
        self.assertFalse(report_path.exists())


if __name__ == "__main__":
    unittest.main()
