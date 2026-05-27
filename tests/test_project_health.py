import tempfile
import unittest
from pathlib import Path

from core.project_health import (
    build_project_health_snapshot,
    format_project_health_panel,
    format_service_modes,
    latency_summary,
    memory_backup_health,
    memory_artifact_summary,
    project_change_summary,
    recent_execution_summary,
    run_estagiario_preflight,
    service_mode_summary,
    startup_health,
    text_health,
    validate_project_jsons,
)


class ProjectHealthTests(unittest.TestCase):
    def test_validate_project_jsons_reports_invalid_memory_file(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "routines.json").write_text('{"ok": true}', encoding="utf-8")
            (memory / "ui_state.json").write_text("{invalid", encoding="utf-8")

            ok, errors = validate_project_jsons(root)

            self.assertEqual(ok, ["memory/routines.json"])
            self.assertEqual(len(errors), 1)
            self.assertIn("memory/ui_state.json", errors[0])

    def test_project_change_summary_handles_non_git_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            summary = project_change_summary(Path(temp_dir))

            self.assertEqual(summary, "sem repositorio git local detectado")

    def test_run_estagiario_preflight_returns_stable_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_estagiario_preflight(Path(temp_dir))

            self.assertIn("compiled_modules", result)
            self.assertIn("compile_error", result)
            self.assertIn("json_ok_count", result)
            self.assertIn("json_errors", result)
            self.assertIn("change_summary", result)

    def test_memory_artifact_summary_counts_runtime_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "ui_state.json").write_text("{}", encoding="utf-8")
            (memory / "handoff.tmp").write_text("tmp", encoding="utf-8")
            (memory / "page.html").write_text("<html></html>", encoding="utf-8")
            (memory / "visible.txt").write_text("texto", encoding="utf-8")

            result = memory_artifact_summary(root)

            self.assertEqual(result["json"], 1)
            self.assertEqual(result["tmp"], 1)
            self.assertEqual(result["html"], 1)
            self.assertEqual(result["txt"], 1)

    def test_memory_backup_health_reports_snapshots(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            backup = root / "memory" / "backups" / "memory-20260525-100000"
            backup.mkdir(parents=True)
            (backup / "manifest.json").write_text('{"files":["ui_state.json"],"created_at":1}', encoding="utf-8")

            result = memory_backup_health(root)

            self.assertEqual(result["count"], 1)
            self.assertEqual(result["latest"]["name"], "memory-20260525-100000")

    def test_text_health_reports_mojibake_candidates(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "bad.md").write_text("Relat\u00c3\u00b3rio quebrado.", encoding="utf-8")

            result = text_health(root)

            self.assertEqual(result["status"], "precisa de revisao")
            self.assertEqual(result["findings"][0]["path"], "bad.md")

    def test_startup_health_reports_logs_and_recent_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            tmp = root / ".tmp"
            tmp.mkdir()
            (tmp / "axel-startup.log").write_text("[agora] Bootstrap do Axel iniciado.\n", encoding="utf-8")
            (tmp / "axel-startup-output.log").write_text("PermissionError: log ocupado\n", encoding="utf-8")

            result = startup_health(root)

            self.assertTrue(result["diagnostic_log_exists"])
            self.assertTrue(result["output_log_exists"])
            self.assertEqual(result["recent_errors"], ["PermissionError: log ocupado"])

    def test_recent_execution_summary_reports_errors(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "execution_log.jsonl").write_text(
                '{"event":"assistant_output","data":{"message":"ok"}}\n'
                '{"event":"tool_error","data":{"message":"Erro ao abrir"}}\n',
                encoding="utf-8",
            )

            result = recent_execution_summary(root)

            self.assertEqual(result["events_count"], 2)
            self.assertEqual(result["recent_errors"], ["Erro ao abrir"])

    def test_recent_execution_summary_reports_route_and_action_telemetry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "execution_log.jsonl").write_text(
                '{"event":"route_result","data":{"source":"turn","input":"???","intent":"respond","target":null,"group":"","detector":"","checked_detectors":20}}\n'
                '{"event":"route_result","data":{"source":"turn","input":"abrir chrome","intent":"open_app","target":"chrome","group":"apps","detector":"detect_open_app","checked_detectors":3}}\n'
                '{"event":"command_execute_end","data":{"action":"file_delete","risk_level":"critical","duration_ms":1500,"success":false,"error":"negado"}}\n',
                encoding="utf-8",
            )

            result = recent_execution_summary(root)

            self.assertEqual(result["events_count"], 3)
            self.assertEqual(result["recent_routes"][-1]["group"], "apps")
            self.assertEqual(result["no_match_routes"][0]["input"], "???")
            self.assertEqual(result["slow_actions"][0]["action"], "file_delete")
            self.assertEqual(result["high_risk_actions"][0]["risk_level"], "critical")
            self.assertEqual(result["recent_errors"], ["negado"])

    def test_latency_summary_groups_actions_and_orders_by_slowest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            memory = root / "memory"
            memory.mkdir()
            (memory / "execution_log.jsonl").write_text(
                '{"event":"command_execute_end","data":{"action":"open_app","duration_ms":200}}\n'
                '{"event":"command_execute_end","data":{"action":"open_app","duration_ms":400}}\n'
                '{"event":"command_execute_end","data":{"action":"daily_briefing","duration_ms":1500}}\n'
                '{"event":"assistant_output","data":{"message":"ignorar"}}\n',
                encoding="utf-8",
            )

            result = latency_summary(root)

            self.assertEqual(result["measured_count"], 3)
            self.assertEqual(result["avg_ms"], 700.0)
            self.assertEqual(result["slow_count"], 1)
            self.assertEqual(result["top_slowest_actions"][0]["action"], "daily_briefing")
            self.assertEqual(result["top_slowest_actions"][1]["avg_ms"], 300.0)
            self.assertEqual(result["recommendations"][0]["action"], "daily_briefing")
            self.assertEqual(result["recommendations"][0]["mode"], "background_with_cache")

    def test_format_project_health_panel_summarizes_snapshot(self):
        snapshot = {
            "status": "saudavel",
            "preflight": {
                "compiled_modules": ["main.py"],
                "compile_error": "",
                "json_ok_count": 2,
                "json_errors": [],
                "change_summary": "limpo",
            },
            "execution": {"events_count": 3, "recent_errors": []},
            "latency": {
                "measured_count": 2,
                "avg_ms": 450.0,
                "slow_count": 0,
                "slow_threshold_ms": 1000,
                "top_slowest_actions": [{"action": "open_app", "max_ms": 600, "avg_ms": 450}],
                "recommendations": [],
            },
            "actions": {"count": 10, "categories": {}, "error": ""},
            "artifacts": {"json": 4, "tmp": 1, "html": 2, "txt": 3},
            "backups": {"count": 0, "latest": {}, "critical_files": 16},
            "text": {"mojibake_count": 0, "findings": [], "status": "ok"},
            "startup": {
                "diagnostic_log_exists": True,
                "output_log_exists": True,
                "recent_errors": [],
            },
            "background": {
                "total": 2,
                "running": 1,
                "failed": 0,
                "succeeded": 1,
                "latest": {},
                "recent": [
                    {
                        "name": "daily_briefing",
                        "status": "succeeded",
                        "duration_ms": 123.4,
                        "message": "Resumo pronto",
                    }
                ],
            },
            "services": {
                "always_on": {
                    "investment_background_refresh": {"enabled": False, "started": False},
                    "reminders_loop": {"enabled": True},
                },
                "on_demand": {
                    "news": {"enabled": True, "configured": False},
                    "training": {"enabled": True},
                },
                "integrations": {},
            },
        }

        result = format_project_health_panel(snapshot)

        self.assertIn("Saude do Axel: projeto saudavel.", result)
        self.assertIn("Compilacao ok em 1 modulos-chave.", result)
        self.assertIn("Actions registradas: 10.", result)
        self.assertIn("carteira em background desligado", result)
        self.assertIn("Startup Windows: atalho nao verificado; diagnostico pronto; saida do processo pronta.", result)
        self.assertIn("Latencia: 2 comandos medidos; media 450.0 ms", result)
        self.assertIn("Maior gargalo recente: open_app max 600 ms, media 450 ms.", result)
        self.assertIn("Background runtime: 1 rodando, 0 falhas, 1 concluidas.", result)
        self.assertIn("Background recente: daily_briefing:succeeded 123ms msg=Resumo pronto.", result)
        self.assertIn("Backups de memoria: nenhum snapshot", result)
        self.assertIn("Encoding textual: sem mojibake detectado", result)

    def test_format_project_health_panel_mentions_telemetry_alerts(self):
        snapshot = {
            "status": "saudavel",
            "preflight": {
                "compiled_modules": ["main.py"],
                "compile_error": "",
                "json_ok_count": 2,
                "json_errors": [],
                "change_summary": "limpo",
            },
            "execution": {
                "events_count": 3,
                "recent_errors": [],
                "no_match_routes": [{"input": "???"}],
                "slow_actions": [{"action": "daily_briefing", "duration_ms": 1200}],
                "high_risk_actions": [{"action": "file_delete", "risk_level": "critical"}],
            },
            "latency": {
                "measured_count": 3,
                "avg_ms": 700.0,
                "slow_count": 1,
                "slow_threshold_ms": 1000,
                "top_slowest_actions": [{"action": "daily_briefing", "max_ms": 1500, "avg_ms": 1500}],
                "recommendations": [
                    {
                        "action": "daily_briefing",
                        "mode": "background_with_cache",
                        "reason": "acao recorrente ou pesada; mover para background e reaproveitar resultado recente",
                    }
                ],
            },
            "actions": {"count": 10, "categories": {}, "error": ""},
            "artifacts": {"json": 4, "tmp": 1, "html": 2, "txt": 3},
            "backups": {"count": 2, "latest": {"name": "memory-20260525-100000"}, "critical_files": 16},
            "text": {"mojibake_count": 1, "findings": [{"path": "tools/briefing_tools.py", "markers": 3}]},
            "startup": {
                "diagnostic_log_exists": True,
                "output_log_exists": True,
                "recent_errors": ["PermissionError: log ocupado"],
            },
            "background": {
                "total": 1,
                "running": 0,
                "failed": 1,
                "succeeded": 0,
                "latest": {},
                "recent": [
                    {
                        "name": "image_analyze_screen",
                        "status": "failed",
                        "duration_ms": 900,
                        "error": "modelo visual indisponivel",
                    }
                ],
            },
            "services": {
                "always_on": {
                    "investment_background_refresh": {"enabled": False, "started": False},
                    "reminders_loop": {"enabled": True},
                },
                "on_demand": {
                    "news": {"enabled": True, "configured": False},
                    "training": {"enabled": True},
                },
                "integrations": {},
            },
        }

        result = format_project_health_panel(snapshot)

        self.assertIn("Startup com alerta recente: PermissionError: log ocupado.", result)
        self.assertIn("Rotas sem match: 1 recentes", result)
        self.assertIn("Acao lenta recente: daily_briefing em 1200 ms.", result)
        self.assertIn("Acao de risco recente: file_delete (critical).", result)
        self.assertIn("Recomendacao de performance: daily_briefing -> background_with_cache", result)
        self.assertIn("Background runtime: 0 rodando, 1 falhas, 0 concluidas.", result)
        self.assertIn("Background recente: image_analyze_screen:failed 900ms erro=modelo visual indisponivel.", result)
        self.assertIn("Backups de memoria: 2 snapshots", result)
        self.assertIn("Encoding textual: 1 arquivo(s) com sinais de mojibake", result)

    def test_format_project_health_panel_mentions_outdated_startup_entry(self):
        snapshot = {
            "status": "precisa de atencao",
            "preflight": {
                "compiled_modules": ["main.py"],
                "compile_error": "",
                "json_ok_count": 2,
                "json_errors": [],
                "change_summary": "limpo",
            },
            "execution": {"events_count": 0, "recent_errors": []},
            "latency": {
                "measured_count": 0,
                "avg_ms": 0,
                "slow_count": 0,
                "slow_threshold_ms": 1000,
                "top_slowest_actions": [],
                "recommendations": [],
            },
            "actions": {"count": 10, "categories": {}, "error": ""},
            "artifacts": {"json": 4, "tmp": 1, "html": 2, "txt": 3},
            "backups": {"count": 0, "latest": {}, "critical_files": 16},
            "text": {"mojibake_count": 0, "findings": [], "status": "ok"},
            "startup": {
                "diagnostic_log_exists": False,
                "output_log_exists": False,
                "recent_errors": [],
                "startup_entry": {"outdated": True},
            },
            "background": {"total": 0, "running": 0, "failed": 0, "succeeded": 0, "latest": {}},
            "services": {
                "always_on": {
                    "investment_background_refresh": {"enabled": False, "started": False},
                    "reminders_loop": {"enabled": True},
                },
                "on_demand": {},
                "integrations": {},
            },
        }

        result = format_project_health_panel(snapshot)

        self.assertIn("Startup Windows com alerta: atalho desatualizado", result)

    def test_build_project_health_snapshot_has_panel_keys(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "memory").mkdir()

            result = build_project_health_snapshot(root)

            self.assertIn("status", result)
            self.assertIn("preflight", result)
            self.assertIn("execution", result)
            self.assertIn("latency", result)
            self.assertIn("artifacts", result)
            self.assertIn("backups", result)
            self.assertIn("startup", result)
            self.assertIn("background", result)
            self.assertIn("actions", result)
            self.assertIn("services", result)
            self.assertIn("text", result)

    def test_service_mode_summary_separates_background_and_on_demand(self):
        result = service_mode_summary()

        self.assertIn("always_on", result)
        self.assertIn("on_demand", result)
        self.assertIn("investment_background_refresh", result["always_on"])
        self.assertIn("news", result["on_demand"])

    def test_format_service_modes_mentions_background_and_training(self):
        snapshot = {
            "services": {
                "always_on": {
                    "investment_background_refresh": {"enabled": False, "started": False},
                    "reminders_loop": {"enabled": True},
                },
                "on_demand": {
                    "news": {"enabled": True, "configured": True},
                    "training": {"enabled": True},
                },
                "integrations": {},
            }
        }

        result = format_service_modes(snapshot)

        self.assertIn("carteira em background desligado", result)
        self.assertIn("treinos sob demanda", result)


if __name__ == "__main__":
    unittest.main()
