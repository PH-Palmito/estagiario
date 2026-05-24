import tempfile
import unittest
import wave
from pathlib import Path

import numpy as np

from voice.audio_files import save_wav, tts_cache_path, wav_duration_seconds, write_raw_pcm_to_wav


class VoiceAudioFilesTests(unittest.TestCase):
    def test_save_wav_and_duration_seconds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.wav"
            audio = np.array([0.0, 0.5, -0.5, 1.5], dtype=np.float32)

            save_wav(path, audio, sample_rate=4)

            self.assertAlmostEqual(wav_duration_seconds(path), 1.0)

    def test_wav_duration_returns_default_for_invalid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid.wav"
            path.write_text("not wav", encoding="utf-8")

            self.assertEqual(wav_duration_seconds(path, default=3.5), 3.5)

    def test_tts_cache_path_is_deterministic_and_creates_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            first = tts_cache_path("piper", "ola", ["a", "b"], cache_root=tmpdir)
            second = tts_cache_path("piper", "ola", ["a", "b"], cache_root=tmpdir)

            self.assertEqual(first, second)
            self.assertEqual(first.suffix, ".wav")
            self.assertTrue(first.parent.exists())

    def test_write_raw_pcm_to_wav(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "raw.wav"

            write_raw_pcm_to_wav(path, b"\x00\x00\xff\x7f", sample_rate=16000)

            with wave.open(str(path), "rb") as wav_file:
                self.assertEqual(wav_file.getnchannels(), 1)
                self.assertEqual(wav_file.getsampwidth(), 2)
                self.assertEqual(wav_file.getframerate(), 16000)
                self.assertEqual(wav_file.getnframes(), 2)


if __name__ == "__main__":
    unittest.main()
