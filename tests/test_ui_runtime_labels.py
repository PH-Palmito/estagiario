import unittest

from core.ui_runtime_labels import assistant_style_label, ui_mode_label, voice_profile_label


class UIRuntimeLabelTests(unittest.TestCase):
    def test_assistant_style_label_prefers_explicit_style(self):
        self.assertEqual(assistant_style_label({"assistant_style": "jarvis", "assistant_humor_style": "seco"}), "jarvis")
        self.assertEqual(assistant_style_label({"assistant_style": "axel", "assistant_humor_style": "jarvis"}), "axel")

    def test_assistant_style_label_falls_back_to_humor(self):
        self.assertEqual(assistant_style_label({"assistant_humor_enabled": True, "assistant_humor_style": "seco"}), "seco")
        self.assertEqual(assistant_style_label({"assistant_humor_enabled": False, "assistant_humor_style": "seco"}), "padrao")

    def test_voice_profile_label_priority(self):
        self.assertEqual(voice_profile_label({"voice_profile": "natural", "piper_voice": "faber"}), "natural")
        self.assertEqual(voice_profile_label({"tts_voice": "tts"}), "tts")
        self.assertEqual(voice_profile_label({}), "faber")

    def test_ui_mode_label_priority(self):
        self.assertEqual(ui_mode_label(dictation_mode=True, conversation_mode=True, waiting_for_direct_response=True), "ditado")
        self.assertEqual(ui_mode_label(dictation_mode=False, conversation_mode=True, waiting_for_direct_response=True), "conversa")
        self.assertEqual(ui_mode_label(dictation_mode=False, conversation_mode=False, waiting_for_direct_response=True), "resposta")
        self.assertEqual(ui_mode_label(dictation_mode=False, conversation_mode=False, waiting_for_direct_response=False), "comando")


if __name__ == "__main__":
    unittest.main()
