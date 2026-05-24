import unittest
from unittest.mock import patch

from voice.audio_playback import play_wav, play_wav_chunk, wait_for_wav_playback


class AudioPlaybackTests(unittest.TestCase):
    def test_wait_for_wav_playback_returns_false_when_duration_finishes(self):
        ticks = iter([0.0, 0.04, 0.2])
        sleeps = []

        interrupted = wait_for_wav_playback(
            "voice.wav",
            duration_seconds=lambda _path: 0.05,
            interrupt_pressed=lambda: False,
            now=lambda: next(ticks),
            sleep=sleeps.append,
        )

        self.assertFalse(interrupted)
        self.assertEqual(sleeps, [0.03])

    def test_wait_for_wav_playback_stops_when_interrupted(self):
        with patch("voice.audio_playback.stop_playback") as stop:
            interrupted = wait_for_wav_playback(
                "voice.wav",
                duration_seconds=lambda _path: 1.0,
                interrupt_pressed=lambda: True,
                now=lambda: 0.0,
                sleep=lambda _seconds: None,
            )

        self.assertTrue(interrupted)
        stop.assert_called_once_with()

    def test_play_wav_skips_wait_when_disabled(self):
        with patch("voice.audio_playback.play_wav_async") as play:
            interrupted = play_wav(
                "voice.wav",
                duration_seconds=lambda _path: 1.0,
                interrupt_pressed=lambda: True,
                wait_for_playback=False,
            )

        self.assertFalse(interrupted)
        play.assert_called_once_with("voice.wav")

    def test_play_wav_chunk_always_waits(self):
        with (
            patch("voice.audio_playback.play_wav_async") as play,
            patch("voice.audio_playback.wait_for_wav_playback", return_value=True) as wait,
        ):
            interrupted = play_wav_chunk(
                "chunk.wav",
                duration_seconds=lambda _path: 1.0,
                interrupt_pressed=lambda: False,
            )

        self.assertTrue(interrupted)
        play.assert_called_once_with("chunk.wav")
        wait.assert_called_once()


if __name__ == "__main__":
    unittest.main()
