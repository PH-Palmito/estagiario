import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from tools import briefing_tools


class BriefingCacheTests(unittest.TestCase):
    def test_daily_briefing_reuses_fresh_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "briefing_cache.json"
            calls = []

            with (
                patch.object(briefing_tools, "BRIEFING_CACHE_PATH", cache_path),
                patch.object(briefing_tools, "time", return_value=1000),
                patch.object(briefing_tools, "_build_daily_briefing", side_effect=lambda: calls.append("build") or "Briefing novo"),
            ):
                first = briefing_tools.daily_briefing()
                second = briefing_tools.daily_briefing()

        self.assertEqual(first, "Briefing novo")
        self.assertEqual(second, "Briefing novo")
        self.assertEqual(calls, ["build"])

    def test_daily_briefing_refreshes_expired_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "briefing_cache.json"
            cache_path.write_text(json.dumps({"created_at": 0, "text": "velho"}), encoding="utf-8")

            with (
                patch.object(briefing_tools, "BRIEFING_CACHE_PATH", cache_path),
                patch.object(briefing_tools, "time", return_value=1000),
                patch.object(briefing_tools, "_build_daily_briefing", return_value="novo"),
            ):
                result = briefing_tools.daily_briefing(ttl_seconds=10)

        self.assertEqual(result, "novo")

    def test_daily_briefing_can_bypass_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "briefing_cache.json"
            cache_path.write_text(json.dumps({"created_at": 1000, "text": "cache"}), encoding="utf-8")

            with (
                patch.object(briefing_tools, "BRIEFING_CACHE_PATH", cache_path),
                patch.object(briefing_tools, "_build_daily_briefing", return_value="direto"),
            ):
                result = briefing_tools.daily_briefing(use_cache=False)

        self.assertEqual(result, "direto")

    def test_invalid_cache_is_ignored(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            cache_path = Path(temp_dir) / "briefing_cache.json"
            cache_path.write_text("{invalid", encoding="utf-8")

            with (
                patch.object(briefing_tools, "BRIEFING_CACHE_PATH", cache_path),
                patch.object(briefing_tools, "_build_daily_briefing", return_value="recuperado"),
            ):
                result = briefing_tools.daily_briefing()

        self.assertEqual(result, "recuperado")

    def test_daily_briefing_includes_explicit_day_focus(self):
        with (
            patch.object(briefing_tools, "_time_greeting", return_value="Bom dia."),
            patch.object(briefing_tools, "_climate_brief", return_value="Clima ok."),
            patch.object(briefing_tools, "_short_agenda_brief", return_value="Agenda livre."),
            patch.object(briefing_tools, "_investment_brief", return_value="Carteira monitorada."),
            patch.object(briefing_tools, "_dividend_agenda_brief", return_value=""),
            patch.object(briefing_tools, "_portfolio_radar_brief", return_value="Radar ok."),
            patch.object(briefing_tools, "todo_brief_summary", return_value="Proximo avanco sugerido: revisar agenda."),
            patch.object(briefing_tools, "_short_reminders_brief", return_value=""),
        ):
            result = briefing_tools.daily_briefing(use_cache=False)

        self.assertIn("Foco do dia: revisar agenda.", result)

    def test_focus_brief_summary_has_fallback_when_no_task_exists(self):
        with patch.object(briefing_tools, "todo_brief_summary", return_value="Sem tarefas em aberto de destaque."):
            result = briefing_tools.focus_brief_summary()

        self.assertEqual(
            result,
            "Foco do dia: escolha uma prioridade curta e finalize antes de abrir novas frentes.",
        )

    def test_investment_brief_reports_daily_change_on_market_day(self):
        snapshot = {"metric_map": {"patrimonio": "R$ 10.500,00", "rentabilidade": "12,00%"}}
        history = [{"date": "2026-06-02", "patrimonio_value": 10000.0, "rentabilidade_percent": 11.0}]

        with (
            patch.object(briefing_tools, "_today", return_value=date(2026, 6, 3)),
            patch.object(briefing_tools, "_current_hour", return_value=11),
            patch.object(briefing_tools, "load_investment_snapshot", return_value=snapshot),
            patch.object(briefing_tools, "_load_investment_history", return_value=history),
        ):
            result = briefing_tools._investment_brief()

        self.assertEqual(result, "Mercado segue em alta para sua carteira, 5,0%.")

    def test_investment_brief_reports_close_after_market(self):
        snapshot = {"metric_map": {"patrimonio": "R$ 9.800,00"}}
        history = [{"date": "2026-06-02", "patrimonio_value": 10000.0}]

        with (
            patch.object(briefing_tools, "_today", return_value=date(2026, 6, 3)),
            patch.object(briefing_tools, "_current_hour", return_value=18),
            patch.object(briefing_tools, "load_investment_snapshot", return_value=snapshot),
            patch.object(briefing_tools, "_load_investment_history", return_value=history),
        ):
            result = briefing_tools._investment_brief()

        self.assertEqual(result, "Mercado fechou em baixa para sua carteira, 2,0%.")

    def test_investment_brief_reports_week_change_on_friday(self):
        snapshot = {"metric_map": {"patrimonio": "R$ 10.700,00"}}
        history = [
            {"date": "2026-06-01", "patrimonio_value": 10000.0},
            {"date": "2026-06-04", "patrimonio_value": 10300.0},
        ]

        with (
            patch.object(briefing_tools, "_today", return_value=date(2026, 6, 5)),
            patch.object(briefing_tools, "_current_hour", return_value=18),
            patch.object(briefing_tools, "load_investment_snapshot", return_value=snapshot),
            patch.object(briefing_tools, "_load_investment_history", return_value=history),
        ):
            result = briefing_tools._investment_brief()

        self.assertEqual(result, "Carteira fechou a semana em alta, 7,0%.")

    def test_investment_brief_uses_visible_variation_when_history_is_missing(self):
        snapshot = {
            "metric_map": {
                "patrimonio": "R$ 7.983,36",
                "valor investido": "R$ 8.981,00",
                "variacao": "-11.11%",
                "rentabilidade": "11,94%",
            }
        }

        with (
            patch.object(briefing_tools, "_today", return_value=date(2026, 6, 10)),
            patch.object(briefing_tools, "_current_hour", return_value=18),
            patch.object(briefing_tools, "load_investment_snapshot", return_value=snapshot),
            patch.object(briefing_tools, "_load_investment_history", return_value=[]),
        ):
            result = briefing_tools._investment_brief()

        self.assertEqual(
            result,
            "Carteira está abaixo do valor investido em 11,1%; ainda falta histórico diário para comparar com ontem.",
        )

    def test_closed_market_brief_skips_dividends_and_radar(self):
        with (
            patch.object(briefing_tools, "_today", return_value=date(2026, 6, 4)),
            patch.object(briefing_tools, "_time_greeting", return_value="Bom dia."),
            patch.object(briefing_tools, "_climate_brief", return_value="Clima ok."),
            patch.object(briefing_tools, "_short_agenda_brief", return_value="Agenda livre."),
            patch.object(briefing_tools, "load_investment_snapshot", return_value={"metric_map": {}}),
            patch.object(briefing_tools, "_dividend_agenda_brief", return_value="Dividendos."),
            patch.object(briefing_tools, "_portfolio_radar_brief", return_value="Radar."),
            patch.object(briefing_tools, "focus_brief_summary", return_value="Foco ok."),
            patch.object(briefing_tools, "_short_reminders_brief", return_value=""),
        ):
            result = briefing_tools.daily_briefing(use_cache=False)

        self.assertIn("Mercado fechado hoje", result)
        self.assertNotIn("Dividendos.", result)
        self.assertNotIn("Radar.", result)


if __name__ == "__main__":
    unittest.main()
