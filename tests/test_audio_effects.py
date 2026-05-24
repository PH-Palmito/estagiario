import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io.wavfile import read as read_wav
from scipy.io.wavfile import write as write_wav

from voice.audio_effects import apply_jarvis_audio_effect, voice_effect_strength


class AudioEffectsTests(unittest.TestCase):
    def test_voice_effect_strength_clamps_invalid_and_out_of_range_values(self):
        self.assertEqual(voice_effect_strength({"assistant_voice_effect_strength": "bad"}), 0.35)
        self.assertEqual(voice_effect_strength({"assistant_voice_effect_strength": -1}), 0.0)
        self.assertEqual(voice_effect_strength({"assistant_voice_effect_strength": 3}), 1.0)

    def test_apply_jarvis_audio_effect_rewrites_enabled_wav(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "voice.wav"
            original = np.array([0, 1000, -1000, 2000, -2000, 0], dtype=np.int16)
            write_wav(path, 16000, original)

            apply_jarvis_audio_effect(
                path,
                {
                    "assistant_voice_effect": "jarvis",
                    "assistant_voice_effect_strength": 0.5,
                },
            )

            sample_rate, processed = read_wav(path)
            self.assertEqual(sample_rate, 16000)
            self.assertEqual(processed.dtype, np.int16)
            self.assertFalse(np.array_equal(processed, original))

    def test_apply_jarvis_audio_effect_skips_when_disabled(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "voice.wav"
            original = np.array([0, 1000, -1000], dtype=np.int16)
            write_wav(path, 16000, original)

            apply_jarvis_audio_effect(path, {"assistant_voice_effect": "none"})

            _sample_rate, processed = read_wav(path)
            self.assertTrue(np.array_equal(processed, original))


if __name__ == "__main__":
    unittest.main()
