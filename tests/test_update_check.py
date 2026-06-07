import tempfile
import unittest
from pathlib import Path

from core.update_check import build_update_snapshot, format_update_report


class UpdateCheckTests(unittest.TestCase):
    def test_build_update_snapshot_reports_git_and_latest_backup(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".git").mkdir()
            (root / "memory" / "backups" / "memory-20260601-120000").mkdir(parents=True)
            (root / "memory" / "backups" / "memory-20260602-120000").mkdir(parents=True)

            result = build_update_snapshot(root)

        self.assertEqual(result["status"], "pronto para plano manual")
        self.assertTrue(result["git_repo"])
        self.assertEqual(result["backup_count"], 2)
        self.assertEqual(result["latest_backup"], "memory-20260602-120000")

    def test_build_update_snapshot_reports_missing_git(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = build_update_snapshot(Path(temp_dir))

        self.assertEqual(result["status"], "precisa de revisao")
        self.assertIn("diretorio .git nao encontrado", result["blockers"])

    def test_format_update_report_is_manual_and_actionable(self):
        snapshot = {
            "status": "pronto para plano manual",
            "git_repo": True,
            "backup_count": 1,
            "latest_backup": "memory-20260602-120000",
            "steps": ["criar backup", "rodar testes"],
            "blockers": [],
        }

        result = format_update_report(snapshot)

        self.assertIn("Update do Axel: pronto para plano manual.", result)
        self.assertIn("Repositorio Git detectado.", result)
        self.assertIn("1. criar backup", result)
        self.assertIn("Atualizacao automatica ainda nao esta liberada", result)


if __name__ == "__main__":
    unittest.main()
