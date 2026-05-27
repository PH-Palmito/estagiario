import unittest
from types import SimpleNamespace

import numpy as np

from voice.listening_runtime import listen_conversation_once, listen_for_hotword, listen_once
from voice.transcription import AudioListenPlan, HotwordDetectionResolution, TranscriptionPlan


class ListeningRuntimeTests(unittest.TestCase):
    def _plan(self, model_size="command"):
        return TranscriptionPlan(
            model_size=model_size,
            prompt=f"{model_size} prompt",
            beam_size=5,
            best_of=4,
            vad_filter=True,
        )

    def test_listen_once_records_and_transcribes_command_audio(self):
        calls = []

        result = listen_once(
            timeout_seconds=6,
            transcription_plan=self._plan(),
            record_audio=lambda timeout: calls.append(("record", timeout)) or np.array([0.1]),
            transcribe_audio=lambda **kwargs: self._transcribe(kwargs, calls, "abrir chrome"),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "abrir chrome")
        self.assertEqual(calls[0], ("record", 6))
        self.assertEqual(calls[1][1]["model_size"], "command")

    def test_listen_once_reports_microphone_failure(self):
        result = listen_once(
            timeout_seconds=6,
            transcription_plan=self._plan(),
            record_audio=lambda _timeout: (_ for _ in ()).throw(RuntimeError("sem mic")),
            transcribe_audio=lambda **_kwargs: SimpleNamespace(ok=True, text="", error=None),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Falha ao acessar o microfone: sem mic")

    def test_listen_conversation_uses_listen_plan_silence_settings(self):
        calls = []

        result = listen_conversation_once(
            listen_plan=AudioListenPlan(timeout_seconds=9, min_speech_seconds=0.3, max_silence_seconds=1.2),
            transcription_plan=self._plan("conversation"),
            record_audio=lambda *args, **kwargs: calls.append(("record", args, kwargs)) or np.array([0.1]),
            transcribe_audio=lambda **kwargs: self._transcribe(kwargs, calls, "continuar conversa"),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "continuar conversa")
        self.assertEqual(calls[0][1], (9,))
        self.assertEqual(calls[0][2]["min_speech_seconds"], 0.3)
        self.assertEqual(calls[1][1]["model_size"], "conversation")

    def test_listen_for_hotword_extracts_inline_command(self):
        calls = []

        result = listen_for_hotword(
            hotword="estagiario",
            listen_plan=AudioListenPlan(timeout_seconds=3, min_speech_seconds=0.2, max_silence_seconds=0.8),
            hotword_plan=self._plan("hotword"),
            command_plan=self._plan("command"),
            record_audio=lambda *args, **kwargs: calls.append(("record", args, kwargs)) or np.array([0.1]),
            transcribe_audio=lambda **kwargs: self._hotword_transcribe(kwargs, calls),
            resolve_hotword_detection=lambda **kwargs: self._resolve_hotword(kwargs),
            contains_hotword=lambda text, hotword: hotword in text,
            extract_inline_command=lambda text, hotword: text.replace(hotword, "").strip(),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.command_text, "abrir chrome")
        self.assertEqual(calls[1][1]["model_size"], "hotword")
        self.assertEqual(calls[2][1]["model_size"], "command")

    def test_listen_for_hotword_reports_transcription_error(self):
        result = listen_for_hotword(
            hotword="estagiario",
            listen_plan=AudioListenPlan(timeout_seconds=3),
            hotword_plan=self._plan("hotword"),
            command_plan=self._plan("command"),
            record_audio=lambda *_args, **_kwargs: np.array([0.1]),
            transcribe_audio=lambda **_kwargs: SimpleNamespace(ok=False, text="", error="ruido"),
            resolve_hotword_detection=lambda **_kwargs: HotwordDetectionResolution(ok=True),
            contains_hotword=lambda _text, _hotword: True,
            extract_inline_command=lambda _text, _hotword: "",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "ruido")

    def _transcribe(self, kwargs, calls, text):
        calls.append(("transcribe", kwargs))
        return SimpleNamespace(ok=True, text=text, error=None)

    def _hotword_transcribe(self, kwargs, calls):
        calls.append(("transcribe", kwargs))
        text = "estagiario" if kwargs["model_size"] == "hotword" else "estagiario abrir chrome"
        return SimpleNamespace(ok=True, text=text, error=None)

    def _resolve_hotword(self, kwargs):
        command_result = kwargs["transcribe_command"]()
        return HotwordDetectionResolution(
            ok=True,
            text=kwargs["hotword_text"],
            command_text=kwargs["extract_inline_command"](command_result.text, kwargs["hotword"]),
        )


if __name__ == "__main__":
    unittest.main()
