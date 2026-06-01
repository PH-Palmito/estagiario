import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from core.study_commands import maybe_handle_study_command


class StudyFileCommandTests(unittest.TestCase):
    def test_study_command_analyzes_attached_files(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "tema.txt"
            path.write_text("Ecossistemas dependem de fluxo de energia e ciclos da materia.", encoding="utf-8")
            shown = []

            result = maybe_handle_study_command(
                f"analisar arquivos anexados: {json.dumps([str(path)])} :: gere questoes",
                lambda: shown.append(True) or "hud",
            )

        self.assertIn("Analise de estudo dos arquivos", result)
        self.assertIn("Questoes para praticar", result)
        self.assertEqual(shown, [True])

    def test_study_command_blocks_corrupted_analysis_response(self):
        corrupted = (
            "Analise de estudo dos arquivos: 1. questoes.pdf: - "
            "T m s t m s m Q u i t q l i l m l m S o n t w i r m "
            "Qumstao ciqxi quivtos cisos lm tmstm couxtmx trivsn qvvat."
        )

        with patch("core.study_commands.analyze_study_files", return_value=corrupted):
            result = maybe_handle_study_command(
                'analisar arquivos anexados: ["C:/fake/questoes.pdf"] :: resuma',
                Mock(return_value="hud"),
            )

        self.assertIn("verificacao de confianca", result)
        self.assertNotIn("T m s t m s", result)

    def test_study_command_handles_followup_before_general_routing(self):
        with patch("core.study_commands.answer_study_followup", return_value="Resposta da questao 1."), patch(
            "core.study_commands.study_snapshot", return_value={}
        ), patch("core.study_commands.update_ui_state"):
            result = maybe_handle_study_command("pode responder a questao 1?", Mock(return_value="hud"))

        self.assertEqual(result, "Resposta da questao 1.")


if __name__ == "__main__":
    unittest.main()
