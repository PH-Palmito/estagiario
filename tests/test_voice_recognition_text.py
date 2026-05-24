import unittest

from voice.recognition_text import (
    command_transcription_score,
    contains_hotword,
    extract_inline_command,
    is_prompt_hallucination,
    normalize_recognized_text,
    should_retry_command_transcription,
)


class VoiceRecognitionTextTests(unittest.TestCase):
    def test_normalize_recognized_text_removes_accents_punctuation_and_spaces(self):
        self.assertEqual(normalize_recognized_text("  Abrir, página   do GitHub!  "), "abrir pagina do github")

    def test_command_score_rewards_known_commands_and_penalizes_noise(self):
        self.assertGreater(command_transcription_score("abrir chrome"), 1.0)
        self.assertLess(command_transcription_score("what is this"), 0.0)

    def test_retry_decision_flags_short_low_score_or_english_noise(self):
        self.assertFalse(should_retry_command_transcription("abrir"))
        self.assertTrue(should_retry_command_transcription("what is this"))
        self.assertTrue(should_retry_command_transcription("zumba ploc"))

    def test_prompt_hallucination_detects_prompt_fragments(self):
        self.assertTrue(is_prompt_hallucination("Transcreva sempre em português do Brasil."))
        self.assertFalse(is_prompt_hallucination("abrir Spotify"))

    def test_extract_inline_command_after_exact_or_fuzzy_hotword(self):
        self.assertEqual(extract_inline_command("estagiário abrir chrome", "estagiario"), "abrir chrome")
        self.assertEqual(extract_inline_command("estagario tocar rock", "estagiario"), "tocar rock")
        self.assertEqual(extract_inline_command("estagiario", "estagiario"), "")

    def test_contains_hotword_accepts_fuzzy_matches(self):
        self.assertTrue(contains_hotword("estagiario", "estagiario"))
        self.assertTrue(contains_hotword("estagario", "estagiario"))
        self.assertFalse(contains_hotword("abrir chrome", "estagiario"))


if __name__ == "__main__":
    unittest.main()
