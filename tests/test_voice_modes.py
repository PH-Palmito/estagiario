import unittest

from core.voice_modes import (
    format_dictation_text,
    is_conversation_stop,
    is_dictation_start,
    is_dictation_stop,
    is_transcription_artifact,
    is_unreliable_conversation_text,
)


class VoiceModeTests(unittest.TestCase):
    def test_conversation_stop_commands(self):
        self.assertTrue(is_conversation_stop("voltar comandos"))
        self.assertTrue(is_conversation_stop("parar conversa"))
        self.assertFalse(is_conversation_stop("vamos conversar"))

    def test_dictation_start_and_stop_commands(self):
        self.assertTrue(is_dictation_start("modo ditado"))
        self.assertTrue(is_dictation_stop("encerrar ditado"))
        self.assertFalse(is_dictation_stop("ditado"))

    def test_format_dictation_special_tokens(self):
        self.assertEqual(format_dictation_text("nova linha"), "\r\n")
        self.assertEqual(format_dictation_text("novo parágrafo"), "\r\n\r\n")
        self.assertEqual(format_dictation_text("tabulação"), "\t")
        self.assertEqual(format_dictation_text("  texto normal  "), "texto normal")

    def test_transcription_artifact_detection(self):
        self.assertTrue(is_transcription_artifact("Legendas pela comunidade de Amara.org"))
        self.assertTrue(is_transcription_artifact("transcreva comandos curtos em portugues do brasil"))
        self.assertFalse(is_transcription_artifact("abrir chrome"))

    def test_unreliable_conversation_filters_empty_short_and_promptish_text(self):
        self.assertTrue(is_unreliable_conversation_text(""))
        self.assertTrue(is_unreliable_conversation_text("a"))
        self.assertTrue(is_unreliable_conversation_text("vocabulario esperado para comandos curtos"))
        self.assertFalse(is_unreliable_conversation_text("um dois testando o microfone"))


if __name__ == "__main__":
    unittest.main()
