import unittest

from core.deferred_runtime import run_deferred


class DeferredRuntimeTests(unittest.TestCase):
    def test_run_deferred_executes_task_and_logs_success(self):
        calls = []

        thread = run_deferred("unit", lambda: calls.append("ran"), log_event=lambda event, **payload: calls.append((event, payload)))
        thread.join(timeout=2)

        self.assertIn("ran", calls)
        self.assertIn(("deferred_task_completed", {"name": "unit"}), calls)

    def test_run_deferred_logs_failure(self):
        calls = []

        def boom():
            raise RuntimeError("falha")

        thread = run_deferred("unit", boom, log_event=lambda event, **payload: calls.append((event, payload)))
        thread.join(timeout=2)

        self.assertEqual(calls[0][0], "deferred_task_failed")
        self.assertEqual(calls[0][1]["name"], "unit")
        self.assertEqual(calls[0][1]["error"], "falha")


if __name__ == "__main__":
    unittest.main()
