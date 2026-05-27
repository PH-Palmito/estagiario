import os
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

from voice.transcription import TranscriptionResolution
from voice.transcription_runtime import WhisperTranscriptionConfig, transcribe_audio


class _Segment:
    def __init__(self, text):
        self.text = text


class _Model:
    def __init__(self, calls):
        self.calls = calls

    def transcribe(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return [_Segment(" abrir "), _Segment("chrome")], SimpleNamespace(language_probability=0.9)


class TranscriptionRuntimeTests(unittest.TestCase):
    def test_rejects_audio_without_signal(self):
        result = self._transcribe(audio_has_signal=lambda _audio: False)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Nao detectei fala no microfone.")

    def test_transcribes_with_model_and_removes_temp_file(self):
        calls = []
        temp_paths = []

        def save_temp_wav(_audio):
            handle = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
            handle.close()
            temp_paths.append(handle.name)
            return handle.name

        result = self._transcribe(calls=calls, save_temp_wav=save_temp_wav)

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "abrir chrome")
        self.assertEqual(calls[0][1]["beam_size"], 5)
        self.assertFalse(os.path.exists(temp_paths[0]))

    def test_returns_resolution_error_from_text_resolver(self):
        result = self._transcribe(
            resolve_transcription_text=lambda *_args, **_kwargs: TranscriptionResolution(
                ok=False,
                text="",
                error="Nao captei com precisao.",
            )
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Nao captei com precisao.")

    def _transcribe(self, **overrides):
        calls = overrides.pop("calls", [])
        save_temp_wav = overrides.pop("save_temp_wav", lambda _audio: "")
        params = {
            "audio": np.array([0.2], dtype=np.float32),
            "model_size": "command",
            "prompt": "command prompt",
            "beam_size": 5,
            "best_of": 5,
            "vad_filter": True,
            "preprocess": True,
            "config": WhisperTranscriptionConfig(
                command_model_size="command",
                command_prompt="command prompt",
                command_rescue_prompt="rescue prompt",
            ),
            "audio_has_signal": lambda _audio: True,
            "preprocess_audio": lambda audio: audio,
            "save_temp_wav": save_temp_wav,
            "get_model": lambda _model_size: _Model(calls),
            "resolve_transcription_text": lambda text, **_kwargs: TranscriptionResolution(ok=True, text=text),
            "is_prompt_hallucination": lambda _text: False,
            "should_retry_command_transcription": lambda _text: False,
            "command_transcription_score": lambda _text: 0.0,
        }
        params.update(overrides)
        return transcribe_audio(**params)


if __name__ == "__main__":
    unittest.main()
