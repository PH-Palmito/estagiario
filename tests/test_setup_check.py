import tempfile
import unittest
from pathlib import Path

from core.setup_check import build_setup_snapshot, format_setup_report


class SetupCheckTests(unittest.TestCase):
    def test_build_setup_snapshot_reports_ready_when_required_items_exist(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / ".env").write_text("AXEL_GEMINI_API_KEY=x\n", encoding="utf-8")

            result = build_setup_snapshot(
                root,
                env={
                    "AXEL_GEMINI_API_KEY": "x",
                    "AXEL_TELEGRAM_BOT_TOKEN": "token",
                    "AXEL_TELEGRAM_ALLOWED_CHAT_IDS": "123",
                },
                module_available=lambda _name: True,
                python_version=(3, 11, 0),
            )

        self.assertEqual(result["status"], "pronto")
        self.assertEqual(result["blockers"], [])
        self.assertTrue(any(item["name"] == "Telegram" and item["status"] == "ok" for item in result["optional"]))

    def test_build_setup_snapshot_reports_required_blockers(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            result = build_setup_snapshot(
                root,
                env={},
                module_available=lambda name: name not in {"sounddevice", "faster_whisper"},
                python_version=(3, 10, 9),
            )

        blocker_names = [item["name"] for item in result["blockers"]]
        self.assertEqual(result["status"], "precisa de configuracao")
        self.assertIn("Python", blocker_names)
        self.assertIn("Arquivo .env", blocker_names)
        self.assertIn("Dependencias de voz", blocker_names)

    def test_format_setup_report_summarizes_next_step(self):
        snapshot = {
            "status": "precisa de configuracao",
            "blockers": [{"name": "Arquivo .env", "detail": "copie .env.example para .env"}],
            "required": [{"name": "Arquivo .env", "status": "acao", "detail": "copie .env.example para .env"}],
            "optional": [{"name": "Telegram", "status": "acao", "detail": "configure token"}],
        }

        result = format_setup_report(snapshot)

        self.assertIn("Setup do Axel: precisa de configuracao.", result)
        self.assertIn("Pendencias obrigatorias: 1.", result)
        self.assertIn("Proximo passo: Arquivo .env", result)


if __name__ == "__main__":
    unittest.main()
