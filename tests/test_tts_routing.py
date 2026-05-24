import unittest
from dataclasses import dataclass

from voice.tts_routing import (
    INTERRUPTED_TTS_ERROR,
    selected_tts_engine,
    speak_with_tts_routing,
    tts_can_fallback_to_piper,
    tts_can_fallback_to_windows,
    tts_has_piper_model,
)


@dataclass
class FakeResult:
    ok: bool
    error: str | None = None
    text: str | None = None


class TtsRoutingTests(unittest.TestCase):
    def test_selected_tts_engine_normalizes_preference(self):
        self.assertEqual(selected_tts_engine({"tts_engine": " Piper "}), "piper")
        self.assertEqual(selected_tts_engine({}), "windows")

    def test_fallback_preferences_default_to_enabled(self):
        self.assertTrue(tts_can_fallback_to_piper({}))
        self.assertTrue(tts_can_fallback_to_windows({}))
        self.assertFalse(tts_can_fallback_to_piper({"gemini_tts_fallback_to_piper": False}))
        self.assertFalse(tts_can_fallback_to_windows({"piper_fallback_to_windows": False}))

    def test_tts_has_piper_model_requires_non_empty_path(self):
        self.assertTrue(tts_has_piper_model({"piper_model_path": " model.onnx "}))
        self.assertFalse(tts_has_piper_model({"piper_model_path": " "}))
        self.assertFalse(tts_has_piper_model({}))

    def test_gemini_success_returns_without_fallback(self):
        calls = []

        result = speak_with_tts_routing(
            "ola",
            "pt-BR",
            {"tts_engine": "gemini", "piper_model_path": "model.onnx"},
            lambda text: calls.append(("gemini", text)) or FakeResult(ok=True, text=text),
            lambda text: calls.append(("piper", text)) or FakeResult(ok=True, text=text),
            lambda text, culture: calls.append(("windows", text, culture)) or FakeResult(ok=True, text=text),
        )

        self.assertTrue(result.ok)
        self.assertEqual(calls, [("gemini", "ola")])

    def test_gemini_failure_tries_piper_when_model_is_configured(self):
        calls = []

        result = speak_with_tts_routing(
            "ola",
            "pt-BR",
            {"tts_engine": "gemini", "piper_model_path": "model.onnx"},
            lambda text: calls.append(("gemini", text)) or FakeResult(ok=False, error="gemini falhou"),
            lambda text: calls.append(("piper", text)) or FakeResult(ok=True, text=text),
            lambda text, culture: calls.append(("windows", text, culture)) or FakeResult(ok=True, text=text),
        )

        self.assertTrue(result.ok)
        self.assertEqual(calls, [("gemini", "ola"), ("piper", "ola")])

    def test_gemini_failure_uses_windows_when_piper_has_no_model(self):
        calls = []

        result = speak_with_tts_routing(
            "ola",
            "pt-BR",
            {"tts_engine": "gemini"},
            lambda text: calls.append(("gemini", text)) or FakeResult(ok=False, error="gemini falhou"),
            lambda text: calls.append(("piper", text)) or FakeResult(ok=True, text=text),
            lambda text, culture: calls.append(("windows", text, culture)) or FakeResult(ok=True, text=text),
        )

        self.assertTrue(result.ok)
        self.assertEqual(calls, [("gemini", "ola"), ("windows", "ola", "pt-BR")])

    def test_gemini_failure_returns_when_fallback_is_disabled(self):
        calls = []

        result = speak_with_tts_routing(
            "ola",
            None,
            {"tts_engine": "gemini", "gemini_tts_fallback_to_piper": False, "piper_model_path": "model.onnx"},
            lambda text: calls.append(("gemini", text)) or FakeResult(ok=False, error="gemini falhou"),
            lambda text: calls.append(("piper", text)) or FakeResult(ok=True, text=text),
            lambda text, culture: calls.append(("windows", text, culture)) or FakeResult(ok=True, text=text),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "gemini falhou")
        self.assertEqual(calls, [("gemini", "ola")])

    def test_interrupted_result_never_falls_back(self):
        calls = []

        result = speak_with_tts_routing(
            "ola",
            None,
            {"tts_engine": "piper", "piper_fallback_to_windows": True},
            lambda text: calls.append(("gemini", text)) or FakeResult(ok=True, text=text),
            lambda text: calls.append(("piper", text)) or FakeResult(ok=False, error=INTERRUPTED_TTS_ERROR),
            lambda text, culture: calls.append(("windows", text, culture)) or FakeResult(ok=True, text=text),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error, INTERRUPTED_TTS_ERROR)
        self.assertEqual(calls, [("piper", "ola")])

    def test_piper_failure_uses_windows_when_fallback_is_enabled(self):
        calls = []

        result = speak_with_tts_routing(
            "ola",
            "pt-BR",
            {"tts_engine": "piper", "piper_fallback_to_windows": True},
            lambda text: calls.append(("gemini", text)) or FakeResult(ok=True, text=text),
            lambda text: calls.append(("piper", text)) or FakeResult(ok=False, error="piper falhou"),
            lambda text, culture: calls.append(("windows", text, culture)) or FakeResult(ok=True, text=text),
        )

        self.assertTrue(result.ok)
        self.assertEqual(calls, [("piper", "ola"), ("windows", "ola", "pt-BR")])

    def test_unknown_engine_uses_windows(self):
        calls = []

        result = speak_with_tts_routing(
            "ola",
            None,
            {"tts_engine": "desconhecido"},
            lambda text: calls.append(("gemini", text)) or FakeResult(ok=True, text=text),
            lambda text: calls.append(("piper", text)) or FakeResult(ok=True, text=text),
            lambda text, culture: calls.append(("windows", text, culture)) or FakeResult(ok=True, text=text),
        )

        self.assertTrue(result.ok)
        self.assertEqual(calls, [("windows", "ola", None)])


if __name__ == "__main__":
    unittest.main()
