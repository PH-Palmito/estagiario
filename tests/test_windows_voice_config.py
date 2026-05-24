import unittest

from voice.windows_voice_config import (
    COMMAND_MODEL_SIZE,
    SAMPLE_RATE,
    build_voice_runtime_config,
    float_pref,
    int_pref,
)


class WindowsVoiceConfigTests(unittest.TestCase):
    def test_float_and_int_preferences_clamp_invalid_values(self):
        preferences = {
            "audio_silence_threshold": "9",
            "whisper_command_beam_size": "invalid",
        }

        self.assertEqual(float_pref(preferences, "audio_silence_threshold", 0.01, 0.001, 0.2), 0.2)
        self.assertEqual(int_pref(preferences, "whisper_command_beam_size", 5, 1, 10), 5)

    def test_build_voice_runtime_config_collects_hotkeys_and_prompts(self):
        config = build_voice_runtime_config(
            {
                "hotword": "axel",
                "trigger_hotkey": "F10",
                "toggle_listening_hotkey": "F11",
                "conversation_transcription_prompt": "Conversa teste.",
            }
        )

        self.assertEqual(config.hotword, "axel")
        self.assertEqual(config.hotword_prompt, "Palavra de ativacao: axel.")
        self.assertEqual(config.hotkey_name, "F10")
        self.assertEqual(config.toggle_listening_hotkey_name, "F11")
        self.assertEqual(config.conversation_prompt, "Conversa teste.")
        self.assertEqual(config.conversation_model_size, COMMAND_MODEL_SIZE)

    def test_audio_capture_config_uses_runtime_values(self):
        config = build_voice_runtime_config({"audio_silence_threshold": "0.03"})
        audio_config = config.audio_capture_config()

        self.assertEqual(audio_config.sample_rate, SAMPLE_RATE)
        self.assertEqual(audio_config.silence_threshold, 0.03)


if __name__ == "__main__":
    unittest.main()
