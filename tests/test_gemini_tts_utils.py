import unittest

from voice.gemini_tts_utils import gemini_cache_settings, gemini_language_code, gemini_tts_plan, gemini_voice_name


class GeminiTtsUtilsTests(unittest.TestCase):
    def test_gemini_voice_name_and_language_use_defaults_for_blank_values(self):
        preferences = {
            "gemini_tts_voice_name": " ",
            "gemini_tts_language_code": "",
        }

        self.assertEqual(gemini_voice_name(preferences), "Kore")
        self.assertEqual(gemini_language_code(preferences), "pt-BR")

    def test_gemini_voice_name_and_language_strip_configured_values(self):
        preferences = {
            "gemini_tts_voice_name": " Puck ",
            "gemini_tts_language_code": " en-US ",
        }

        self.assertEqual(gemini_voice_name(preferences), "Puck")
        self.assertEqual(gemini_language_code(preferences), "en-US")

    def test_gemini_cache_settings_include_effect_preferences(self):
        result = gemini_cache_settings(
            "Kore",
            "pt-BR",
            "60",
            {
                "assistant_voice_effect": " Jarvis ",
                "assistant_voice_effect_strength": 0.25,
            },
        )

        self.assertEqual(result, ["Kore", "pt-BR", "60", "jarvis", "0.25"])

    def test_gemini_tts_plan_collects_runtime_settings(self):
        result = gemini_tts_plan(
            "ola mundo",
            {
                "gemini_tts_voice_name": " Puck ",
                "gemini_tts_language_code": " en-US ",
                "tts_cache_enabled": True,
                "assistant_voice_effect": " Jarvis ",
                "assistant_voice_effect_strength": 0.5,
            },
            timeout_seconds=45,
        )

        self.assertEqual(result.text, "ola mundo")
        self.assertEqual(result.voice_name, "Puck")
        self.assertEqual(result.language_code, "en-US")
        self.assertEqual(result.timeout_seconds, 45)
        self.assertTrue(result.cache_enabled)
        self.assertEqual(result.cache_settings, ["Puck", "en-US", "45", "jarvis", "0.5"])

    def test_gemini_tts_plan_can_disable_cache(self):
        result = gemini_tts_plan(
            "ola mundo",
            {"tts_cache_enabled": False},
            timeout_seconds=60,
        )

        self.assertFalse(result.cache_enabled)


if __name__ == "__main__":
    unittest.main()
