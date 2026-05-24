import unittest

import numpy as np

from voice.audio_capture import (
    AudioCaptureConfig,
    audio_has_signal,
    chunk_has_speech,
    chunk_levels,
    preprocess_audio,
)


class AudioCaptureTests(unittest.TestCase):
    def _config(self, **overrides):
        values = {
            "sample_rate": 16000,
            "frame_size": 1024,
            "default_max_record_seconds": 6.0,
            "silence_threshold": 0.01,
            "audio_dynamic_threshold": True,
            "audio_noise_multiplier": 3.0,
            "audio_max_dynamic_threshold": 0.04,
            "audio_preroll_seconds": 0.25,
            "audio_normalize_enabled": True,
            "audio_dc_offset_filter": True,
            "audio_target_peak": 0.75,
            "audio_max_gain": 4.0,
        }
        values.update(overrides)
        return AudioCaptureConfig(**values)

    def test_chunk_levels_returns_peak_and_rms(self):
        peak, rms = chunk_levels(np.array([0.0, 0.5, -1.0], dtype=np.float32))

        self.assertEqual(peak, 1.0)
        self.assertAlmostEqual(rms, np.sqrt((0.0 + 0.25 + 1.0) / 3))

    def test_chunk_has_speech_uses_peak_or_rms(self):
        self.assertTrue(chunk_has_speech(np.array([0.0, 0.02], dtype=np.float32), 0.01))
        self.assertFalse(chunk_has_speech(np.array([0.0, 0.001], dtype=np.float32), 0.01))

    def test_preprocess_audio_filters_dc_offset_and_normalizes(self):
        audio = np.array([0.2, 0.4], dtype=np.float32)

        processed = preprocess_audio(audio, self._config(audio_target_peak=0.5, audio_max_gain=10.0))

        self.assertAlmostEqual(float(np.mean(processed)), 0.0, places=6)
        self.assertAlmostEqual(float(np.max(np.abs(processed))), 0.5, places=6)

    def test_audio_has_signal_rejects_empty_and_accepts_threshold(self):
        config = self._config(silence_threshold=0.01)

        self.assertFalse(audio_has_signal(np.array([], dtype=np.float32), config))
        self.assertTrue(audio_has_signal(np.array([0.02], dtype=np.float32), config))


if __name__ == "__main__":
    unittest.main()
