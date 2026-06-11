import unittest
from datetime import datetime

from core.reminder_announcer import ReminderAnnouncer, reminder_message


class ReminderAnnouncerTests(unittest.TestCase):
    def test_formats_single_due_reminder(self):
        self.assertEqual(reminder_message([{"text": "beber agua"}]), "Lembrete: beber agua.")

    def test_formats_single_due_agenda_item(self):
        self.assertEqual(reminder_message([{"text": "reuniao", "source": "agenda"}]), "Agenda: reuniao.")

    def test_formats_agenda_follow_up_prompt(self):
        self.assertEqual(
            reminder_message(
                [
                    {
                        "text": "prova de matematica",
                        "source": "agenda",
                        "follow_up_prompt": "Depois me conta como foi.",
                    }
                ]
            ),
            "Agenda: prova de matematica. Depois me conta como foi.",
        )

    def test_formats_empty_single_reminder(self):
        self.assertEqual(reminder_message([{"text": ""}]), "Voce tem um lembrete vencido.")

    def test_formats_multiple_due_reminders_with_limit(self):
        message = reminder_message(
            [
                {"text": "um"},
                {"text": "dois"},
                {"text": "tres"},
                {"text": "quatro"},
            ]
        )

        self.assertEqual(message, "Lembretes: um; dois; tres.")

    def test_formats_mixed_agenda_and_reminders(self):
        message = reminder_message(
            [
                {"text": "reuniao", "source": "agenda"},
                {"text": "beber agua"},
            ]
        )

        self.assertEqual(message, "Agenda e lembretes: reuniao; beber agua.")

    def test_training_reminder_has_priority(self):
        calls = []
        announcer = ReminderAnnouncer(
            consume_due_training_reminder=lambda: {"text": "hora do treino"},
            consume_due_reminders=lambda: [{"text": "outro"}],
            output_response=lambda *args, **kwargs: calls.append((args, kwargs)),
            now_fn=lambda: 30.0,
        )

        announced = announcer.maybe_announce_due_reminders(True)

        self.assertTrue(announced)
        self.assertEqual(calls[0][0], ("hora do treino", True))
        self.assertTrue(calls[0][1]["interrupt_current_tts"])

    def test_skips_when_checked_recently(self):
        calls = []
        announcer = ReminderAnnouncer(
            consume_due_training_reminder=lambda: {},
            consume_due_reminders=lambda: [{"text": "beber agua"}],
            output_response=lambda *args, **kwargs: calls.append(args),
            now_fn=lambda: 10.0,
            last_check_at=0.0,
        )

        announced = announcer.maybe_announce_due_reminders(True)

        self.assertFalse(announced)
        self.assertEqual(calls, [])

    def test_announces_regular_reminder_after_interval(self):
        calls = []
        announcer = ReminderAnnouncer(
            consume_due_training_reminder=lambda: {},
            consume_due_reminders=lambda: [{"text": "beber agua"}],
            output_response=lambda *args, **kwargs: calls.append((args, kwargs)),
            now_fn=lambda: 25.0,
        )

        announced = announcer.maybe_announce_due_reminders(False)

        self.assertTrue(announced)
        self.assertEqual(calls[0][0], ("Lembrete: beber agua.", False))

    def test_consume_errors_are_ignored(self):
        announcer = ReminderAnnouncer(
            consume_due_training_reminder=lambda: {},
            consume_due_reminders=lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            output_response=lambda *args, **kwargs: None,
            now_fn=lambda: 25.0,
        )

        self.assertFalse(announcer.maybe_announce_due_reminders(True))

    def test_announces_night_sleep_prompt_once(self):
        calls = []
        timestamp = datetime(2026, 6, 10, 23, 30).timestamp()
        announcer = ReminderAnnouncer(
            consume_due_training_reminder=lambda: {},
            consume_due_reminders=lambda: [],
            output_response=lambda *args, **kwargs: calls.append((args, kwargs)),
            now_fn=lambda: timestamp,
            min_interval_seconds=0,
        )

        first = announcer.maybe_announce_due_reminders(False)
        second = announcer.maybe_announce_due_reminders(False)

        self.assertTrue(first)
        self.assertFalse(second)
        self.assertIn("dormir", calls[0][0][0])

    def test_does_not_announce_night_sleep_prompt_during_day(self):
        calls = []
        timestamp = datetime(2026, 6, 10, 15, 0).timestamp()
        announcer = ReminderAnnouncer(
            consume_due_training_reminder=lambda: {},
            consume_due_reminders=lambda: [],
            output_response=lambda *args, **kwargs: calls.append(args),
            now_fn=lambda: timestamp,
            min_interval_seconds=0,
        )

        self.assertFalse(announcer.maybe_announce_due_reminders(False))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
