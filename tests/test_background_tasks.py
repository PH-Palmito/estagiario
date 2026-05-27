import unittest
import tempfile
from pathlib import Path

from core.background_tasks import BackgroundTaskRunner


class ImmediateThread:
    def __init__(self, *, target, name="", daemon=True):
        self.target = target
        self.name = name
        self.daemon = daemon

    def start(self):
        self.target()


class BackgroundTaskTests(unittest.TestCase):
    def test_runner_records_successful_task(self):
        runner = BackgroundTaskRunner(thread_factory=ImmediateThread, history_path=None)

        task_id = runner.submit("briefing", lambda: "ok")

        self.assertEqual(task_id, "bg-1")
        summary = runner.summary()
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["succeeded"], 1)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(summary["latest"]["message"], "ok")
        self.assertEqual(summary["recent"][0]["name"], "briefing")
        self.assertIsNotNone(summary["latest"]["duration_ms"])
        notifications = runner.consume_notifications()
        self.assertEqual(notifications[0]["name"], "briefing")
        self.assertEqual(notifications[0]["status"], "succeeded")
        self.assertEqual(runner.consume_notifications(), [])

    def test_runner_records_failed_task(self):
        runner = BackgroundTaskRunner(thread_factory=ImmediateThread, history_path=None)

        def fail():
            raise RuntimeError("boom")

        runner.submit("visao", fail)

        summary = runner.summary()
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["latest"]["status"], "failed")
        self.assertEqual(summary["latest"]["error"], "boom")
        notifications = runner.consume_notifications()
        self.assertEqual(notifications[0]["status"], "failed")
        self.assertEqual(notifications[0]["error"], "boom")

    def test_runner_sends_finished_task_to_notification_sink(self):
        published = []
        runner = BackgroundTaskRunner(
            thread_factory=ImmediateThread,
            history_path=None,
            notification_sink=lambda item: published.append(item),
        )

        runner.submit("briefing", lambda: "ok")

        self.assertEqual(published[0]["name"], "briefing")
        self.assertEqual(published[0]["status"], "succeeded")
        self.assertEqual(published[0]["message"], "ok")

    def test_latest_result_ignores_running_tasks(self):
        class QueuedThread:
            def __init__(self, *, target, name="", daemon=True):
                self.target = target

            def start(self):
                return None

        runner = BackgroundTaskRunner(thread_factory=ImmediateThread, history_path=None)
        runner.submit("a", lambda: "feito")
        runner.thread_factory = QueuedThread
        runner.submit("b", lambda: "pendente")

        latest = runner.latest_result()

        self.assertEqual(latest["name"], "a")
        self.assertEqual(latest["message"], "feito")

    def test_runner_limits_history(self):
        runner = BackgroundTaskRunner(max_history=2, thread_factory=ImmediateThread, history_path=None)

        runner.submit("a", lambda: "a")
        runner.submit("b", lambda: "b")
        runner.submit("c", lambda: "c")

        snapshot = runner.snapshot()
        self.assertEqual([task["task_id"] for task in snapshot], ["bg-2", "bg-3"])

    def test_runner_persists_finished_tasks_to_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "background_tasks.jsonl"
            runner = BackgroundTaskRunner(thread_factory=ImmediateThread, history_path=history_path)

            runner.submit("briefing", lambda: "feito")

            content = history_path.read_text(encoding="utf-8")
            self.assertIn('"name": "briefing"', content)
            self.assertIn('"message": "feito"', content)

    def test_latest_result_reads_persisted_history_when_memory_is_empty(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "background_tasks.jsonl"
            first = BackgroundTaskRunner(thread_factory=ImmediateThread, history_path=history_path)
            first.submit("briefing", lambda: "persistido")

            second = BackgroundTaskRunner(thread_factory=ImmediateThread, history_path=history_path)
            latest = second.latest_result()

            self.assertEqual(latest["name"], "briefing")
            self.assertEqual(latest["message"], "persistido")

    def test_runner_limits_persisted_history(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            history_path = Path(temp_dir) / "background_tasks.jsonl"
            runner = BackgroundTaskRunner(
                thread_factory=ImmediateThread,
                history_path=history_path,
                max_persisted_history=2,
            )

            runner.submit("a", lambda: "a")
            runner.submit("b", lambda: "b")
            runner.submit("c", lambda: "c")

            lines = history_path.read_text(encoding="utf-8").splitlines()

            self.assertEqual(len(lines), 2)
            self.assertNotIn('"name": "a"', "\n".join(lines))
            self.assertIn('"name": "b"', lines[0])
            self.assertIn('"name": "c"', lines[1])


if __name__ == "__main__":
    unittest.main()
