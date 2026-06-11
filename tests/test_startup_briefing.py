import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from core.startup_briefing import (
    WINDOWS_STARTUP_BRIEFING_DELAY_SECONDS,
    schedule_startup_briefing_worker,
    send_startup_briefing_once,
)


class StartupBriefingTests(unittest.TestCase):
    def _send(self, **overrides):
        with tempfile.TemporaryDirectory() as tmp:
            calls = []
            state_path = Path(tmp) / "startup.json"
            if "state" in overrides:
                state_path.write_text(json.dumps(overrides.pop("state")), encoding="utf-8")

            params = {
                "voice_mode": True,
                "args": ["main.py"],
                "voice_preferences": {},
                "state_path": state_path,
                "greeting_variants": {"briefing_already_delivered": ["ja foi"]},
                "next_phrase": lambda *_args: "ja foi",
                "daily_briefing": lambda: "Briefing do dia",
                "output_response": lambda *args, **kwargs: calls.append((args, kwargs)),
                "now": datetime(2026, 5, 18, 9, 30),
            }
            params.update(overrides)
            result = send_startup_briefing_once(**params)
            saved = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
            return result, calls, saved

    def test_sends_and_records_daily_briefing(self):
        result, calls, saved = self._send()

        self.assertTrue(result)
        self.assertEqual(calls[0][0][:2], ("Briefing do dia", True))
        self.assertEqual(saved["last_briefing_date"], "2026-05-18")

    def test_reports_when_briefing_already_delivered_today(self):
        result, calls, saved = self._send(state={"last_briefing_date": "2026-05-18"})

        self.assertTrue(result)
        self.assertEqual(calls[0][0][:2], ("ja foi", True))
        self.assertEqual(saved["last_briefing_date"], "2026-05-18")

    def test_force_flag_ignores_already_delivered_state(self):
        result, calls, saved = self._send(
            args=["main.py", "--force-startup-briefing"],
            state={"last_briefing_date": "2026-05-18"},
        )

        self.assertTrue(result)
        self.assertEqual(calls[0][0][:2], ("Briefing do dia", True))
        self.assertEqual(saved["last_briefing_date"], "2026-05-18")

    def test_skips_when_disabled_by_flag(self):
        result, calls, saved = self._send(args=["main.py", "--no-startup-briefing"])

        self.assertFalse(result)
        self.assertEqual(calls, [])
        self.assertEqual(saved, {})

    def test_skips_when_preference_disabled(self):
        result, calls, saved = self._send(voice_preferences={"startup_briefing_enabled": False})

        self.assertFalse(result)
        self.assertEqual(calls, [])
        self.assertEqual(saved, {})

    def test_reports_briefing_failure(self):
        result, calls, saved = self._send(daily_briefing=lambda: (_ for _ in ()).throw(RuntimeError("sem dados")))

        self.assertFalse(result)
        self.assertIn("Nao consegui gerar", calls[0][0][0])
        self.assertEqual(saved, {})

    def test_reports_empty_briefing(self):
        result, calls, saved = self._send(daily_briefing=lambda: " ")

        self.assertFalse(result)
        self.assertIn("veio vazio", calls[0][0][0])
        self.assertEqual(saved, {})

    def test_windows_startup_uses_longer_delay(self):
        calls = []

        class FakeThread:
            def __init__(self, *, target, name, daemon):
                self.target = target
                self.name = name
                self.daemon = daemon

            def start(self):
                self.target()

        with (
            patch("core.startup_briefing.time.sleep", side_effect=lambda delay: calls.append(("sleep", delay))),
            patch("core.startup_briefing.Thread", FakeThread),
        ):
            result = schedule_startup_briefing_worker(
                args=["main.py", "--startup"],
                voice_mode=True,
                send_startup_briefing=lambda voice_mode: calls.append(("send", voice_mode)) or True,
            )

        self.assertTrue(result)
        self.assertEqual(calls, [("sleep", WINDOWS_STARTUP_BRIEFING_DELAY_SECONDS), ("send", True)])


if __name__ == "__main__":
    unittest.main()
