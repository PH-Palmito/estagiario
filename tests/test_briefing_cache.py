import json
import tempfile
import unittest
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

        self.assertIn("Foco do dia: proximo avanco sugerido: revisar agenda.", result)

    def test_focus_brief_summary_has_fallback_when_no_task_exists(self):
        with patch.object(briefing_tools, "todo_brief_summary", return_value="Sem tarefas em aberto de destaque."):
            result = briefing_tools.focus_brief_summary()

        self.assertEqual(
            result,
            "Foco do dia: escolha uma prioridade curta e finalize antes de abrir novas frentes.",
        )


if __name__ == "__main__":
    unittest.main()
