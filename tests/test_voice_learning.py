import unittest

from core.voice_learning import (
    VoiceLearningState,
    maybe_learn_correction_for_last_voice,
    maybe_remember_pending_voice_correction,
)


class VoiceLearningTests(unittest.TestCase):
    def test_remembers_pending_voice_correction(self):
        learned = []

        result = maybe_remember_pending_voice_correction(
            object(),
            VoiceLearningState(pending_command_learning_text="abre cromi", last_voice_text="ultimo"),
            command_correction_text=lambda command: "abrir chrome",
            normalize_text=lambda text: text.lower(),
            remember_voice_correction=lambda heard, means: learned.append((heard, means)) or True,
        )

        self.assertTrue(result.learned)
        self.assertEqual(result.heard, "abre cromi")
        self.assertEqual(result.means, "abrir chrome")
        self.assertEqual(result.state.pending_command_learning_text, "")
        self.assertEqual(result.state.last_voice_text, "ultimo")
        self.assertEqual(learned, [("abre cromi", "abrir chrome")])

    def test_does_not_remember_when_pending_is_empty(self):
        result = maybe_remember_pending_voice_correction(
            object(),
            VoiceLearningState(),
            command_correction_text=lambda command: "abrir chrome",
            normalize_text=lambda text: text.lower(),
            remember_voice_correction=lambda heard, means: self.fail("should not learn"),
        )

        self.assertFalse(result.learned)
        self.assertEqual(result.state.pending_command_learning_text, "")

    def test_does_not_remember_when_meaning_is_same(self):
        result = maybe_remember_pending_voice_correction(
            object(),
            VoiceLearningState(pending_command_learning_text="Abrir Chrome"),
            command_correction_text=lambda command: "abrir chrome",
            normalize_text=lambda text: text.lower(),
            remember_voice_correction=lambda heard, means: self.fail("should not learn"),
        )

        self.assertFalse(result.learned)
        self.assertEqual(result.heard, "Abrir Chrome")
        self.assertEqual(result.means, "abrir chrome")

    def test_learns_correction_for_last_voice(self):
        learned = []

        result = maybe_learn_correction_for_last_voice(
            "eu quis dizer abrir chrome",
            VoiceLearningState(last_voice_text="abre cromi"),
            normalize_text=lambda text: text.lower(),
            remember_voice_correction=lambda heard, means: learned.append((heard, means)) or True,
        )

        self.assertEqual(learned, [("abre cromi", "abrir chrome")])
        self.assertEqual(result.state.last_voice_text, "")
        self.assertEqual(result.response, "Aprendi: quando ouvir 'abre cromi', vou entender como 'abrir chrome'.")

    def test_reports_when_no_last_voice_exists(self):
        result = maybe_learn_correction_for_last_voice(
            "corrigir ultimo comando para abrir chrome",
            VoiceLearningState(last_voice_text=""),
            normalize_text=lambda text: text.lower(),
            remember_voice_correction=lambda heard, means: self.fail("should not learn"),
        )

        self.assertEqual(result.response, "Ainda nao tenho uma fala de voz para corrigir.")

    def test_ignores_non_correction_text(self):
        state = VoiceLearningState(last_voice_text="abre cromi")

        result = maybe_learn_correction_for_last_voice(
            "abrir chrome",
            state,
            normalize_text=lambda text: text.lower(),
            remember_voice_correction=lambda heard, means: self.fail("should not learn"),
        )

        self.assertIsNone(result.response)
        self.assertEqual(result.state, state)


if __name__ == "__main__":
    unittest.main()
