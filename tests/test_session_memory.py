import unittest

from memory import session


class SessionMemoryTests(unittest.TestCase):
    def tearDown(self):
        session.clear()

    def test_legacy_history_still_returns_last_three_messages(self):
        for item in ["a", "b", "c", "d"]:
            session.add(item)

        self.assertEqual(session.get(), ["b", "c", "d"])

    def test_structured_turns_are_limited_and_formatted(self):
        for index in range(30):
            session.add_turn("user", f"mensagem {index}", source="unit")

        recent = session.recent_turns(limit=3)

        self.assertEqual(len(recent), 3)
        self.assertEqual(recent[-1]["text"], "mensagem 29")
        self.assertIn("Memoria curta:", session.format_recent_turns(limit=2))


if __name__ == "__main__":
    unittest.main()
