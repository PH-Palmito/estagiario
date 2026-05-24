import json
import tempfile
import unittest
from pathlib import Path

from voice.tts_text import load_tts_pronunciations, prepare_tts_text


class TtsTextTests(unittest.TestCase):
    def test_prepare_tts_text_expands_common_tech_terms_and_time(self):
        result = prepare_tts_text("Abrir GitHub e VS Code as 10h30.")

        self.assertIn("guíti rãb", result)
        self.assertIn("vê ésse côde", result)
        self.assertIn("dez horas e trinta minutos", result)

    def test_prepare_tts_text_expands_currency_percent_and_date(self):
        result = prepare_tts_text("R$ 1.234,56 caiu -2,5% em 03/04/24.")

        self.assertIn("1234 vírgula 56 reais", result)
        self.assertIn("menos 2 vírgula 5 por cento", result)
        self.assertIn("três de abril de dois mil e vinte e quatro", result)

    def test_prepare_tts_text_expands_units(self):
        result = prepare_tts_text("Bateria de 5000 mAh e 128GB.")

        self.assertIn("cinco mil miliampere hora", result)
        self.assertIn("cento e vinte e oito gigabytes", result)

    def test_prepare_tts_text_applies_custom_pronunciations(self):
        result = prepare_tts_text("Codex abriu.", {"Codex": "Codecs"})

        self.assertIn("Codecs", result)

    def test_load_tts_pronunciations_respects_preferences_and_filters_empty_items(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "tts_pronunciations.json"
            path.write_text(json.dumps({"Codex": "Codecs", "": "vazio", "Axel": ""}), encoding="utf-8")

            enabled = load_tts_pronunciations({"tts_pronunciations_enabled": True}, path)
            disabled = load_tts_pronunciations({"tts_pronunciations_enabled": False}, path)

        self.assertEqual(enabled, {"Codex": "Codecs"})
        self.assertEqual(disabled, {})


if __name__ == "__main__":
    unittest.main()
