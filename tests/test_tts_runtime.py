import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from voice.tts_runtime import TtsRuntimeResult, play_wav_result, speak_with_windows_runtime


class TtsRuntimeTests(unittest.TestCase):
    def test_play_wav_result_reports_interrupt(self):
        with patch("voice.tts_runtime.play_wav", return_value=True):
            result = play_wav_result(
                Path("audio.wav"),
                preferences={"tts_wait_for_playback": True},
                interrupt_pressed=lambda: False,
            )

        self.assertEqual(result, TtsRuntimeResult(ok=False, error="Fala interrompida."))

    def test_play_wav_result_uses_wait_preference(self):
        calls = []

        def fake_play_wav(_path, _duration, _interrupt, wait_for_playback):
            calls.append(wait_for_playback)
            return False

        with patch("voice.tts_runtime.play_wav", side_effect=fake_play_wav):
            result = play_wav_result(
                Path("audio.wav"),
                preferences={"tts_wait_for_playback": False},
                interrupt_pressed=lambda: False,
            )

        self.assertIsNone(result)
        self.assertEqual(calls, [False])

    def test_speak_with_windows_runtime_reports_start_failure(self):
        result = speak_with_windows_runtime(
            "ola",
            culture=None,
            preferences={},
            powershell_exe="powershell",
            interrupt_pressed=lambda: False,
            popen=lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("sem processo")),
        )

        self.assertEqual(result, TtsRuntimeResult(ok=False, error="Falha ao iniciar voz sintetizada: sem processo"))

    def test_speak_with_windows_runtime_reports_process_error(self):
        process = SimpleNamespace()

        with patch(
            "voice.tts_runtime.monitor_windows_tts_process",
            return_value=SimpleNamespace(error="", completed=SimpleNamespace(returncode=1, stderr="erro", stdout="")),
        ):
            result = speak_with_windows_runtime(
                "ola",
                culture=None,
                preferences={},
                powershell_exe="powershell",
                interrupt_pressed=lambda: False,
                popen=lambda *_args, **_kwargs: process,
            )

        self.assertEqual(result.ok, False)
        self.assertIn("erro", result.error)

    def test_speak_with_windows_runtime_returns_success(self):
        process = SimpleNamespace()

        with patch(
            "voice.tts_runtime.monitor_windows_tts_process",
            return_value=SimpleNamespace(error="", completed=SimpleNamespace(returncode=0, stderr="", stdout="")),
        ):
            result = speak_with_windows_runtime(
                "ola",
                culture=None,
                preferences={},
                powershell_exe="powershell",
                interrupt_pressed=lambda: False,
                popen=lambda *_args, **_kwargs: process,
            )

        self.assertEqual(result, TtsRuntimeResult(ok=True, text="ola"))


if __name__ == "__main__":
    unittest.main()
