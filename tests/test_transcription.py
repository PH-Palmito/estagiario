import unittest

from voice.transcription import (
    TranscriptionResolution,
    command_transcription_plan,
    conversation_listen_plan,
    conversation_transcription_plan,
    hotword_listen_plan,
    hotword_transcription_plan,
    resolve_hotword_detection,
    resolve_transcription_text,
)


class TranscriptionResolutionTests(unittest.TestCase):
    def test_command_transcription_plan_collects_whisper_settings(self):
        result = command_transcription_plan(
            command_model_size="small",
            command_prompt="prompt",
            whisper_command_beam_size=5,
            whisper_command_best_of=4,
            whisper_command_vad_filter=True,
        )

        self.assertEqual(result.model_size, "small")
        self.assertEqual(result.prompt, "prompt")
        self.assertEqual(result.beam_size, 5)
        self.assertEqual(result.best_of, 4)
        self.assertTrue(result.vad_filter)

    def test_hotword_plans_collect_audio_and_transcription_settings(self):
        listen = hotword_listen_plan(timeout_seconds=3.0, min_speech_seconds=0.1, max_silence_seconds=0.5)
        transcribe = hotword_transcription_plan(
            hotword_model_size="tiny",
            hotword_prompt="hotword",
            whisper_hotword_beam_size=1,
            whisper_hotword_best_of=1,
            whisper_hotword_vad_filter=True,
        )

        self.assertEqual(listen.timeout_seconds, 3.0)
        self.assertEqual(listen.min_speech_seconds, 0.1)
        self.assertEqual(listen.max_silence_seconds, 0.5)
        self.assertEqual(transcribe.model_size, "tiny")
        self.assertEqual(transcribe.prompt, "hotword")
        self.assertTrue(transcribe.vad_filter)

    def test_conversation_plans_collect_audio_and_transcription_settings(self):
        listen = conversation_listen_plan(
            requested_timeout_seconds=None,
            default_timeout_seconds=7.0,
            min_speech_seconds=0.35,
            max_silence_seconds=1.0,
        )
        explicit_listen = conversation_listen_plan(
            requested_timeout_seconds=4.0,
            default_timeout_seconds=7.0,
            min_speech_seconds=0.35,
            max_silence_seconds=1.0,
        )
        transcribe = conversation_transcription_plan(
            conversation_model_size="medium",
            conversation_prompt="conversation",
            whisper_conversation_beam_size=3,
            whisper_conversation_best_of=2,
            whisper_conversation_vad_filter=False,
        )

        self.assertEqual(listen.timeout_seconds, 7.0)
        self.assertEqual(explicit_listen.timeout_seconds, 4.0)
        self.assertEqual(listen.min_speech_seconds, 0.35)
        self.assertEqual(listen.max_silence_seconds, 1.0)
        self.assertEqual(transcribe.model_size, "medium")
        self.assertEqual(transcribe.prompt, "conversation")
        self.assertEqual(transcribe.beam_size, 3)
        self.assertEqual(transcribe.best_of, 2)
        self.assertFalse(transcribe.vad_filter)

    def test_hotword_detection_reports_missing_hotword_without_command_transcription(self):
        calls = []

        result = resolve_hotword_detection(
            hotword_text="abrir chrome",
            hotword="estagiario",
            contains_hotword=lambda _text, _hotword: False,
            transcribe_command=lambda: calls.append("command") or TranscriptionResolution(ok=True, text=""),
            extract_inline_command=lambda _text, _hotword: "",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Hotword nao detectada.")
        self.assertEqual(calls, [])

    def test_hotword_detection_extracts_inline_command_when_command_transcription_succeeds(self):
        result = resolve_hotword_detection(
            hotword_text="estagiario",
            hotword="estagiario",
            contains_hotword=lambda _text, _hotword: True,
            transcribe_command=lambda: TranscriptionResolution(ok=True, text="estagiario abrir chrome"),
            extract_inline_command=lambda text, _hotword: text.replace("estagiario ", ""),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "estagiario")
        self.assertEqual(result.command_text, "abrir chrome")

    def test_hotword_detection_still_succeeds_when_command_transcription_fails(self):
        result = resolve_hotword_detection(
            hotword_text="estagiario",
            hotword="estagiario",
            contains_hotword=lambda _text, _hotword: True,
            transcribe_command=lambda: TranscriptionResolution(ok=False, text="", error="ruido"),
            extract_inline_command=lambda _text, _hotword: "nao usado",
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "estagiario")
        self.assertEqual(result.command_text, "")

    def test_empty_text_reports_no_speech(self):
        result = self._resolve("")

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Nenhuma fala reconhecida.")

    def test_regular_text_returns_unchanged(self):
        result = self._resolve("abrir chrome")

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "abrir chrome")

    def test_prompt_hallucination_uses_clean_rescue_text(self):
        calls = []

        result = self._resolve(
            "prompt hallucination",
            transcribe_once=lambda *args: calls.append(args) or ("abrir chrome", object()),
            is_prompt_hallucination=lambda text: text == "prompt hallucination",
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "abrir chrome")
        self.assertEqual(calls, [(None, 6, 6, False)])

    def test_prompt_hallucination_reports_error_when_rescue_is_still_bad(self):
        result = self._resolve(
            "prompt hallucination",
            transcribe_once=lambda *_args: ("prompt hallucination", object()),
            is_prompt_hallucination=lambda text: text == "prompt hallucination",
            prompt_hallucination_error="Nao captei com precisao.",
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "Nao captei com precisao.")

    def test_weak_command_retry_replaces_text_when_score_improves(self):
        calls = []

        result = self._resolve(
            "what is this",
            transcribe_once=lambda *args: calls.append(args) or ("abrir chrome", object()),
            should_retry_command_transcription=lambda text: text == "what is this",
            command_transcription_score=lambda text: 2.0 if text == "abrir chrome" else 0.0,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "abrir chrome")
        self.assertEqual(calls, [("rescue prompt", 6, 6, False)])

    def test_weak_command_retry_keeps_original_when_rescue_score_is_not_better(self):
        result = self._resolve(
            "zumba ploc",
            transcribe_once=lambda *_args: ("outro ruido", object()),
            should_retry_command_transcription=lambda _text: True,
            command_transcription_score=lambda _text: 0.5,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "zumba ploc")

    def test_non_command_model_does_not_rescue(self):
        calls = []

        result = self._resolve(
            "prompt hallucination",
            model_size="conversation",
            transcribe_once=lambda *args: calls.append(args) or ("abrir chrome", object()),
            is_prompt_hallucination=lambda _text: True,
            should_retry_command_transcription=lambda _text: True,
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "prompt hallucination")
        self.assertEqual(calls, [])

    def _resolve(self, text, **overrides):
        params = {
            "model_size": "command",
            "command_model_size": "command",
            "prompt": "command prompt",
            "command_prompt": "command prompt",
            "command_rescue_prompt": "rescue prompt",
            "beam_size": 5,
            "best_of": 5,
            "prompt_hallucination_error": "prompt error",
            "transcribe_once": lambda *_args: ("", object()),
            "is_prompt_hallucination": lambda _text: False,
            "should_retry_command_transcription": lambda _text: False,
            "command_transcription_score": lambda _text: 0.0,
        }
        params.update(overrides)
        return resolve_transcription_text(text, **params)


if __name__ == "__main__":
    unittest.main()
