import unittest

from core.performance_mode import (
    PERFORMANCE_MODE_BALANCED,
    PERFORMANCE_MODE_ECONOMY,
    PERFORMANCE_MODE_PERFORMANCE,
    normalize_performance_mode,
    performance_settings,
    performance_settings_from_state,
    runtime_idle_sleep_seconds_from_state,
)


class PerformanceModeTests(unittest.TestCase):
    def test_normalizes_aliases(self):
        self.assertEqual(normalize_performance_mode("economia"), PERFORMANCE_MODE_ECONOMY)
        self.assertEqual(normalize_performance_mode("leve"), PERFORMANCE_MODE_ECONOMY)
        self.assertEqual(normalize_performance_mode("normal"), PERFORMANCE_MODE_BALANCED)
        self.assertEqual(normalize_performance_mode("rapido"), PERFORMANCE_MODE_PERFORMANCE)
        self.assertEqual(normalize_performance_mode("???"), PERFORMANCE_MODE_BALANCED)

    def test_economy_mode_reduces_motion_and_polling(self):
        economy = performance_settings("economy")
        balanced = performance_settings("balanced")

        self.assertEqual(economy.mode, PERFORMANCE_MODE_ECONOMY)
        self.assertTrue(economy.reduce_motion)
        self.assertGreater(economy.qt_poll_ms, balanced.qt_poll_ms)
        self.assertGreater(economy.web_frame_delay_ms, balanced.web_frame_delay_ms)
        self.assertLess(economy.animation_scale, balanced.animation_scale)

    def test_performance_mode_increases_responsiveness(self):
        fast = performance_settings("performance")
        balanced = performance_settings("balanced")

        self.assertEqual(fast.mode, PERFORMANCE_MODE_PERFORMANCE)
        self.assertLess(fast.qt_poll_ms, balanced.qt_poll_ms)
        self.assertLess(fast.web_frame_delay_ms, balanced.web_frame_delay_ms)
        self.assertGreater(fast.animation_scale, balanced.animation_scale)

    def test_reads_mode_from_ui_state(self):
        settings = performance_settings_from_state({"performance_mode": "modo leve"})

        self.assertEqual(settings.mode, PERFORMANCE_MODE_ECONOMY)

    def test_runtime_idle_sleep_increases_for_silent_or_economy_modes(self):
        balanced = runtime_idle_sleep_seconds_from_state({"performance_mode": "balanced"})
        economy = runtime_idle_sleep_seconds_from_state({"performance_mode": "economy"})
        silent = runtime_idle_sleep_seconds_from_state({"mode": "silencioso", "performance_mode": "performance"})

        self.assertGreater(economy, balanced)
        self.assertGreater(silent, economy)


if __name__ == "__main__":
    unittest.main()
