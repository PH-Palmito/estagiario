import os
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

from voice.audio_diagnostics import format_audio_stats, run_audio_diagnostic


class AudioDiagnosticsTests(unittest.TestCase):
    def test_format_audio_stats_reports_duration_peak_and_rms(self):
        text = format_audio_stats(
            label="Bruto",
            audio=np.array([0.0, 0.5], dtype=np.float32),
            sample_rate=2,
            chunk_levels=lambda _audio: (0.5, 0.25),
        )

        self.assertEqual(text, "Bruto: duracao=1.00s pico=0.5000 rms=0.2500")

    def test_run_audio_diagnostic_records_saves_and_transcribes_both_versions(self):
        saved = []
        transcribed = []
        raw_audio = np.array([0.2, 0.4], dtype=np.float32)

        with tempfile.TemporaryDirectory() as temp_dir:
            previous_cwd = os.getcwd()
            os.chdir(temp_dir)
            try:
                report = run_audio_diagnostic(
                    seconds=20.0,
                    default_seconds=3.0,
                    sample_rate=2,
                    command_model_size="command",
                    command_prompt="prompt",
                    whisper_command_beam_size=5,
                    whisper_command_best_of=4,
                    whisper_command_vad_filter=True,
                    active_input_device_info=lambda: {"name": "Mic Teste"},
                    record_fixed_audio=lambda duration: self._record(duration, raw_audio),
                    preprocess_audio=lambda audio: audio * 2,
                    save_wav=lambda path, audio: saved.append((str(path), audio.copy())),
                    transcribe_audio=lambda audio, **kwargs: self._transcribe(audio, kwargs, transcribed),
                    chunk_levels=lambda audio: (float(np.max(np.abs(audio))), 0.1),
                )
            finally:
                os.chdir(previous_cwd)

        self.assertIn("Microfone usado: Mic Teste", report)
        self.assertIn("Whisper bruto: audio 0.6", report)
        self.assertIn("Whisper processado: audio 1.2", report)
        self.assertEqual(len(saved), 2)
        self.assertEqual(saved[0][0].split(os.sep)[-1][:10], "audio_raw_")
        self.assertEqual(transcribed[0]["beam_size"], 5)
        self.assertTrue(np.array_equal(saved[1][1], raw_audio * 2))

    def test_run_audio_diagnostic_reports_recording_failure(self):
        report = run_audio_diagnostic(
            seconds=None,
            default_seconds=3.0,
            sample_rate=2,
            command_model_size="command",
            command_prompt="prompt",
            whisper_command_beam_size=5,
            whisper_command_best_of=4,
            whisper_command_vad_filter=True,
            active_input_device_info=lambda: None,
            record_fixed_audio=lambda _duration: (_ for _ in ()).throw(RuntimeError("sem mic")),
            preprocess_audio=lambda audio: audio,
            save_wav=lambda _path, _audio: None,
            transcribe_audio=lambda _audio, **_kwargs: SimpleNamespace(ok=True, text="", error=None),
            chunk_levels=lambda _audio: (0.0, 0.0),
        )

        self.assertEqual(report, "Falha ao gravar diagnostico de audio: sem mic")

    def _record(self, duration, audio):
        self.assertEqual(duration, 15.0)
        return audio

    def _transcribe(self, audio, kwargs, transcribed):
        transcribed.append(kwargs)
        return SimpleNamespace(ok=True, text=f"audio {float(np.sum(audio)):.1f}", error=None)


if __name__ == "__main__":
    unittest.main()
