import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from voice.piper_speech import prime_piper_cache_runtime, speak_with_piper_runtime
from voice.piper_utils import piper_tts_settings
from voice.tts_runtime import TtsRuntimeResult


class PiperSpeechTests(unittest.TestCase):
    def setUp(self):
        self.previous_cwd = os.getcwd()
        self.temp_dir = tempfile.TemporaryDirectory()
        os.chdir(self.temp_dir.name)

    def tearDown(self):
        os.chdir(self.previous_cwd)
        self.temp_dir.cleanup()

    def test_prime_piper_cache_creates_missing_cache_entry(self):
        calls = []
        effects = []
        settings = piper_tts_settings({"piper_exe_path": "piper.exe"})

        result = prime_piper_cache_runtime(
            [" ola "],
            settings=settings,
            model=Path("voice.onnx"),
            preferences={"tts_cache_enabled": True},
            prepare_tts_text=lambda text: text.upper(),
            apply_audio_effect=lambda path: effects.append(path),
            run_process=lambda command, **kwargs: calls.append((command, kwargs))
            or SimpleNamespace(returncode=0, stderr="", stdout=""),
        )

        self.assertTrue(result.ok)
        self.assertEqual(result.text, "Cache TTS: 1 criado(s), 0 ja existia(m).")
        self.assertEqual(calls[0][0][:4], ["piper.exe", "--model", "voice.onnx", "--output_file"])
        self.assertEqual(calls[0][1]["input"], "OLA")
        self.assertEqual(len(effects), 1)

    def test_prime_piper_cache_reports_first_error_with_counts(self):
        settings = piper_tts_settings({})

        result = prime_piper_cache_runtime(
            ["ola"],
            settings=settings,
            model=Path("voice.onnx"),
            preferences={},
            prepare_tts_text=lambda text: text,
            apply_audio_effect=lambda _path: None,
            run_process=lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stderr="erro piper", stdout=""),
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.text, "Cache TTS: 0 criado(s), 0 ja existia(m).")
        self.assertEqual(result.error, "erro piper")

    def test_speak_with_piper_plays_cached_full_phrase(self):
        played = []
        settings = piper_tts_settings({})
        cache_path = self._cache_path_for("ola", settings)
        cache_path.write_bytes(b"wav")

        result = speak_with_piper_runtime(
            "ola",
            settings=settings,
            model=Path("voice.onnx"),
            preferences={"tts_cache_enabled": True},
            prepare_tts_text=lambda text: text,
            run_piper_synthesis=lambda *_args: self.fail("cache should skip synthesis"),
            play_wav=lambda path: played.append(path) or None,
            play_wav_chunk=lambda _path: self.fail("full phrase should not play chunks"),
        )

        self.assertTrue(result.ok)
        self.assertEqual(played, [cache_path])

    def test_speak_with_piper_synthesizes_and_plays_uncached_phrase(self):
        synthesized = []
        played = []
        copied = []
        settings = piper_tts_settings({})

        result = speak_with_piper_runtime(
            "ola",
            settings=settings,
            model=Path("voice.onnx"),
            preferences={"tts_cache_enabled": True},
            prepare_tts_text=lambda text: text,
            run_piper_synthesis=lambda text, output, *_args: synthesized.append((text, output)) or None,
            play_wav=lambda path: played.append(path) or None,
            play_wav_chunk=lambda _path: self.fail("full phrase should not play chunks"),
            copy_file=lambda source, target: copied.append((source, target)),
        )

        self.assertTrue(result.ok)
        self.assertEqual(synthesized[0][0], "ola")
        self.assertEqual(played, [str(copied[0][1])])
        self.assertFalse(Path(synthesized[0][1]).exists())

    def test_speak_with_piper_returns_synthesis_error(self):
        settings = piper_tts_settings({})

        result = speak_with_piper_runtime(
            "ola",
            settings=settings,
            model=Path("voice.onnx"),
            preferences={"tts_cache_enabled": False},
            prepare_tts_text=lambda text: text,
            run_piper_synthesis=lambda *_args: TtsRuntimeResult(ok=False, error="falhou"),
            play_wav=lambda _path: None,
            play_wav_chunk=lambda _path: None,
        )

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "falhou")

    def _cache_path_for(self, text, settings):
        from voice.audio_files import tts_cache_path
        from voice.piper_speech import piper_cache_key_settings

        return tts_cache_path(
            "piper",
            text,
            piper_cache_key_settings(settings, Path("voice.onnx"), {"tts_cache_enabled": True}),
        )


if __name__ == "__main__":
    unittest.main()
