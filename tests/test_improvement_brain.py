import unittest

from core.improvement_brain import ImprovementBrain


class ImprovementBrainTests(unittest.TestCase):
    def test_refresh_runs_steps_and_updates_timestamp(self):
        calls = []
        brain = ImprovementBrain(
            steps=[lambda: calls.append("a"), lambda: calls.append("b")],
            now_fn=lambda: 20.0,
        )

        refreshed = brain.refresh()

        self.assertTrue(refreshed)
        self.assertEqual(calls, ["a", "b"])
        self.assertEqual(brain.last_refresh_at, 20.0)

    def test_refresh_is_throttled_without_force(self):
        calls = []
        brain = ImprovementBrain(
            steps=[lambda: calls.append("a")],
            now_fn=lambda: 25.0,
            last_refresh_at=20.0,
            min_interval_seconds=15.0,
        )

        refreshed = brain.refresh()

        self.assertFalse(refreshed)
        self.assertEqual(calls, [])

    def test_force_refresh_ignores_throttle(self):
        calls = []
        brain = ImprovementBrain(
            steps=[lambda: calls.append("a")],
            now_fn=lambda: 25.0,
            last_refresh_at=20.0,
            min_interval_seconds=15.0,
        )

        refreshed = brain.refresh(force=True)

        self.assertTrue(refreshed)
        self.assertEqual(calls, ["a"])

    def test_refresh_failure_is_ignored(self):
        brain = ImprovementBrain(
            steps=[lambda: (_ for _ in ()).throw(RuntimeError("boom"))],
            now_fn=lambda: 20.0,
        )

        self.assertFalse(brain.refresh())

    def test_announces_codex_suggestion(self):
        calls = []
        brain = ImprovementBrain(
            steps=[],
            consume_codex_suggestion=lambda: "avance isso",
            output_response=lambda *args, **kwargs: calls.append((args, kwargs)),
        )

        announced = brain.maybe_announce_codex_suggestion(True)

        self.assertTrue(announced)
        self.assertEqual(calls, [(("avance isso", True), {})])

    def test_skips_empty_codex_suggestion(self):
        brain = ImprovementBrain(
            steps=[],
            consume_codex_suggestion=lambda: "",
            output_response=lambda *args, **kwargs: None,
        )

        self.assertFalse(brain.maybe_announce_codex_suggestion(True))


if __name__ == "__main__":
    unittest.main()
