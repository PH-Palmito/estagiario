import unittest
from unittest.mock import patch

from core.router_voice import detect_voice_correction_command


class RouterVoiceTests(unittest.TestCase):
    @patch("core.router_voice.list_voice_corrections", return_value=[])
    def test_lists_empty_voice_corrections(self, _list_voice_corrections):
        result = detect_voice_correction_command("listar correcoes de voz")

        self.assertEqual(result, {"intent": "respond", "target": None, "response": "Nenhuma correcao de voz salva."})

    @patch(
        "core.router_voice.list_voice_corrections",
        return_value=[{"heard": "chegar", "means": "fechar"}],
    )
    def test_lists_voice_corrections(self, _list_voice_corrections):
        result = detect_voice_correction_command("ver correcoes")

        self.assertEqual(result["intent"], "respond")
        self.assertIn("quando ouvir 'chegar'", result["response"])

    @patch("core.router_voice.remember_voice_correction", return_value=True)
    def test_teaches_voice_correction(self, remember_voice_correction):
        result = detect_voice_correction_command("quando eu disser chegar entenda como fechar")

        remember_voice_correction.assert_called_once_with("chegar", "fechar")
        self.assertEqual(result["intent"], "respond")
        self.assertIn("Aprendi", result["response"])

    @patch("core.router_voice.forget_voice_correction", return_value=True)
    def test_forgets_voice_correction(self, forget_voice_correction):
        result = detect_voice_correction_command("remova correcao de voz chegar")

        forget_voice_correction.assert_called_once_with("chegar")
        self.assertEqual(result["response"], "Esqueci a correcao de voz para 'chegar'.")


if __name__ == "__main__":
    unittest.main()
