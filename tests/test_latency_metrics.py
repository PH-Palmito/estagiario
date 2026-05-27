import unittest

from core.latency_metrics import duration_ms, log_latency_stage


class LatencyMetricsTests(unittest.TestCase):
    def test_duration_ms_never_goes_negative(self):
        self.assertEqual(duration_ms(10.0, now_fn=lambda: 9.0), 0.0)

    def test_log_latency_stage_records_standard_event(self):
        events = []

        log_latency_stage(
            lambda event, **payload: events.append((event, payload)),
            "routing",
            1.0,
            now_fn=lambda: 1.12345,
            source="unit",
        )

        self.assertEqual(events[0][0], "latency_stage")
        self.assertEqual(events[0][1]["stage"], "routing")
        self.assertEqual(events[0][1]["duration_ms"], 123.45)
        self.assertEqual(events[0][1]["source"], "unit")


if __name__ == "__main__":
    unittest.main()
