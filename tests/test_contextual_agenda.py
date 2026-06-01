import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from memory import agenda
from memory import reminders
from memory.reminders import parse_reminder_request


class ContextualAgendaTests(unittest.TestCase):
    def test_add_exam_by_day_suggests_study_reminders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "agenda.json"
            with (
                patch.object(agenda, "AGENDA_PATH", path),
                patch.object(agenda, "_today", return_value=datetime(2026, 5, 28).date()),
                patch("memory.agenda.datetime") as dt,
            ):
                dt.now.return_value = datetime(2026, 5, 28, 9, 0)
                dt.min = datetime.min
                dt.combine = datetime.combine

                result = agenda.add_agenda_item("prova de matematica dia 12")

        self.assertIn("Compromisso registrado para 12/06: prova de matematica.", result)
        self.assertIn("Quer que eu adicione lembretes para estudar", result)

    def test_add_exam_tomorrow_keeps_tomorrow_and_skips_study_plan_prompt(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "agenda.json"
            with (
                patch.object(agenda, "AGENDA_PATH", path),
                patch.object(agenda, "_today", return_value=datetime.now().date()),
            ):
                result = agenda.add_agenda_item("prova amanha me lembre")

        self.assertIn("Compromisso registrado para amanha: prova.", result)
        self.assertIn("O cronograma entrou no modo coragem", result)
        self.assertNotIn("adicione lembretes para estudar antes", result)

    def test_parse_day_with_time_uses_explicit_day(self):
        due_at, text = parse_reminder_request("prova de matematica dia 12 as 10h", now=datetime(2026, 5, 28, 9, 0))

        self.assertEqual(due_at, datetime(2026, 6, 12, 10, 0))
        self.assertEqual(text, "prova de matematica")

    def test_incomplete_reminder_accepts_time_reply(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            reminders_path = Path(temp_dir) / "reminders.json"
            pending_path = Path(temp_dir) / "pending_reminder.json"
            with (
                patch.object(reminders, "REMINDERS_PATH", reminders_path),
                patch.object(reminders, "PENDING_REMINDER_PATH", pending_path),
                patch.object(reminders, "sync_memory_state_safely"),
            ):
                first = reminders.add_reminder("amanha eu tenho uma prova")
                second = reminders.add_reminder("7h da manha")

        self.assertEqual(first, "Quando devo lembrar isso?")
        self.assertIn("Combinado. Vou lembrar", second)
        self.assertIn("eu tenho uma prova", second)


if __name__ == "__main__":
    unittest.main()
