import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from memory import piper_voice_manager, training, tts_pronunciations, voice_corrections, voice_profiles


class VoiceMemoryFilesTests(unittest.TestCase):
    def test_tts_pronunciations_recover_and_update(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tts_pronunciations.json"
            path.write_text("{invalid", encoding="utf-8")

            with patch.object(tts_pronunciations, "TTS_PRONUNCIATIONS_PATH", path):
                self.assertEqual(tts_pronunciations.load_tts_pronunciations(), {})
                tts_pronunciations.set_tts_pronunciation("Axel", "áquicel")
                self.assertEqual(tts_pronunciations.get_tts_pronunciation("axel"), "áquicel")
                self.assertTrue(tts_pronunciations.remove_tts_pronunciation("AXEL"))
                self.assertIsNone(tts_pronunciations.get_tts_pronunciation("Axel"))

    def test_voice_corrections_recover_update_and_increment_usage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "voice_corrections.json"
            path.write_text("{invalid", encoding="utf-8")

            with patch.object(voice_corrections, "VOICE_CORRECTIONS_PATH", path):
                self.assertEqual(voice_corrections.load_voice_corrections(), [])
                self.assertTrue(voice_corrections.remember_voice_correction("chegar", "fechar"))
                self.assertEqual(voice_corrections.apply_voice_correction("chegar"), "fechar")
                loaded = voice_corrections.load_voice_corrections()
                self.assertEqual(loaded[0]["uses"], 1)
                self.assertTrue(voice_corrections.forget_voice_correction("chegar"))

    def test_voice_profile_updates_preferences_atomically(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "voice_preferences.json"
            path.write_text("{invalid", encoding="utf-8")

            with patch.object(voice_profiles, "VOICE_PREFERENCES_PATH", path):
                ok, message = voice_profiles.apply_voice_profile("natural")
                preferences = voice_profiles.load_preferences()

            self.assertTrue(ok)
            self.assertIn("natural", message)
            self.assertEqual(preferences["assistant_style"], "natural")

    def test_piper_voice_apply_updates_preferences_when_installed(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pref = root / "voice_preferences.json"
            model = root / "models" / "pt_BR-faber-medium" / "pt_BR-faber-medium.onnx"
            config = root / "models" / "pt_BR-faber-medium" / "pt_BR-faber-medium.onnx.json"
            model.parent.mkdir(parents=True)
            model.write_text("model", encoding="utf-8")
            config.write_text("config", encoding="utf-8")

            with (
                patch.object(piper_voice_manager, "VOICE_PREFERENCES_PATH", pref),
                patch.object(piper_voice_manager, "PIPER_MODELS_DIR", root / "models"),
            ):
                ok, message = piper_voice_manager.apply_piper_voice("pt_BR-faber-medium")
                preferences = piper_voice_manager.load_preferences()

            self.assertTrue(ok, message)
            self.assertEqual(preferences["tts_engine"], "piper")
            self.assertEqual(preferences["piper_model_path"], str(model))

    def test_training_state_recovers_and_normalizes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "training.json"
            path.write_text("{invalid", encoding="utf-8")

            with (
                patch.object(training, "TRAINING_PATH", path),
                patch.object(training, "sync_memory_state_safely"),
            ):
                loaded = training.load_training_state()
                saved = training.save_training_state({"completed": "bad", "reminder": {"enabled": False}})

            self.assertEqual(loaded["completed"], [])
            self.assertEqual(saved["completed"], [])
            self.assertFalse(saved["reminder"]["enabled"])
            self.assertIn("time", saved["reminder"])


if __name__ == "__main__":
    unittest.main()
